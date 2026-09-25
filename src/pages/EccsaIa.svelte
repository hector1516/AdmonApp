<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { online } from '$lib/stores/online.js';

	// ECCSA IA - Chat estilo LLM con historial de 7 días

	let conversaciones = $state([]);
	let mensajes = $state([]);
	let conversacionActual = $state(null);
	let nuevoMensaje = $state('');
	let enviando = $state(false);
	let loading = $state(true);
	let loadingMsg = $state(false);
	let error = $state('');
	let panelAbierto = $state(true); // sidebar en desktop

	const MAX_HISTORY_DAYS = 7;

	function tieneAcceso() {
		try {
			const u = JSON.parse(localStorage.getItem('admon_user') || 'null');
			return !!(u && u.acceso_ia);
		} catch {
			return false;
		}
	}

	function apiHeaders() {
		return { 'Content-Type': 'application/json', ...auth.authHeader() };
	}

	async function cargarConversaciones() {
		try {
			const res = await fetch('/api/ia/conversaciones', { headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al cargar conversaciones.');
			conversaciones = data || [];
			// Auto-seleccionar la más reciente si no hay seleccionada
			if (!conversacionActual && conversaciones.length > 0) {
				await seleccionarConversacion(conversaciones[0].IdConversacion);
			}
		} catch (e) {
			error = e.message === 'Sesión expirada' ? e.message : 'No se pudo cargar conversaciones.';
		} finally {
			loading = false;
		}
	}

	async function seleccionarConversacion(id) {
		loadingMsg = true;
		error = '';
		try {
			const res = await fetch(`/api/ia/conversaciones/${id}/mensajes`, { headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al cargar mensajes.');
			mensajes = data || [];
			conversacionActual = conversaciones.find(c => c.IdConversacion === id) || null;
		} catch (e) {
			error = e.message === 'Sesión expirada' ? e.message : 'No se pudo cargar mensajes.';
		} finally {
			loadingMsg = false;
			// Cerrar sidebar en móvil
			if (window.innerWidth < 768) panelAbierto = false;
		}
	}

	async function nuevaConversacion() {
		error = '';
		try {
			const res = await fetch('/api/ia/conversaciones', {
				method: 'POST',
				headers: apiHeaders(),
				body: JSON.stringify({ titulo: 'Nueva conversación' })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al crear conversación.');
			await cargarConversaciones();
			// Seleccionar la nueva
			if (data.IdConversacion) {
				await seleccionarConversacion(data.IdConversacion);
			}
		} catch (e) {
			error = e.message || 'Error al crear conversación.';
		}
	}

	async function enviarMensaje() {
		if (!nuevoMensaje.trim() || !conversacionActual || enviando) return;
		const texto = nuevoMensaje.trim();
		nuevoMensaje = '';
		enviando = true;
		error = '';

		// Agregar mensaje del usuario optimista
		const msgUsuario = {
			IdMensaje: Date.now(), // temporal
			Rol: 'user',
			Contenido: texto,
			FechaCreacion: new Date().toISOString()
		};
		mensajes = [...mensajes, msgUsuario];

		try {
			const res = await fetch(`/api/ia/conversaciones/${conversacionActual.IdConversacion}/mensajes`, {
				method: 'POST',
				headers: apiHeaders(),
				body: JSON.stringify({ contenido: texto })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al enviar.');

			// Reemplazar mensaje optimista con respuesta real (incluye respuesta del assistant)
			mensajes = data.mensajes || [];
			// Actualizar título si es la primera conversación
			if (conversacionActual.Titulo === 'Nueva conversación' && data.titulo) {
				conversacionActual.Titulo = data.titulo;
				const idx = conversaciones.findIndex(c => c.IdConversacion === conversacionActual.IdConversacion);
				if (idx >= 0) conversaciones[idx].Titulo = data.titulo;
			}
		} catch (e) {
			error = e.message || 'Error al enviar mensaje.';
			// Remover mensaje optimista en error
			mensajes = mensajes.filter(m => m.IdMensaje !== msgUsuario.IdMensaje);
		} finally {
			enviando = false;
		}
	}

	async function eliminarConversacion(id) {
		if (!confirm('¿Eliminar esta conversación y todos sus mensajes?')) return;
		error = '';
		try {
			const res = await fetch(`/api/ia/conversaciones/${id}`, { method: 'DELETE', headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al eliminar.');
			if (conversacionActual?.IdConversacion === id) {
				conversacionActual = null;
				mensajes = [];
			}
			await cargarConversaciones();
		} catch (e) {
			error = e.message || 'Error al eliminar.';
		}
	}

	function formatearFecha(fecha) {
		if (!fecha) return '';
		const d = new Date(fecha);
		const hoy = new Date();
		const ayer = new Date(hoy);
		ayer.setDate(ayer.getDate() - 1);
		
		if (d.toDateString() === hoy.toDateString()) {
			return 'Hoy ' + d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
		}
		if (d.toDateString() === ayer.toDateString()) {
			return 'Ayer ' + d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
		}
		return d.toLocaleDateString('es-MX', { day: '2-digit', month: '2-digit', year: 'numeric' });
	}

	function primeraLinea(texto) {
		return String(texto || '').split('\n')[0].slice(0, 50);
	}

	onMount(async () => {
		if (!auth.isLoggedIn()) {
			navigate('/login', { replace: true });
			return;
		}
		if (!tieneAcceso()) {
			navigate('/dashboard', { replace: true });
			return;
		}
		await cargarConversaciones();
	});
</script>

<div class="ia-page">
	<!-- Sidebar conversaciones -->
	<aside class="ia-sidebar" class:open={panelAbierto} class:closed={!panelAbierto && window.innerWidth < 768}>
		<div class="sidebar-header">
			<h2>💬 ECCSA IA</h2>
			<button class="btn btn-ghost" on:click={nuevaConversacion} title="Nueva conversación">➕</button>
		</div>

		{#if loading}
			<div class="sidebar-loading">Cargando…</div>
		{:else if conversaciones.length === 0}
			<div class="sidebar-empty">
				<p>Sin conversaciones aún</p>
				<button class="btn btn-primary btn-sm" on:click={nuevaConversacion}>➕ Iniciar chat</button>
			</div>
		{:else}
			<div class="sidebar-list">
				{#each conversaciones as c (c.IdConversacion)}
					<button 
						class="sidebar-item" 
						class:active={conversacionActual?.IdConversacion === c.IdConversacion}
						on:click={() => seleccionarConversacion(c.IdConversacion)}
					>
						<div class="item-info">
							<div class="item-titulo">{c.Titulo || 'Nueva conversación'}</div>
							<div class="item-fecha">{formatearFecha(c.FechaActualizacion)}</div>
						</div>
						<button class="btn-delete" on:click={(e) => { e.stopPropagation(); eliminarConversacion(c.IdConversacion); }} title="Eliminar">🗑️</button>
					</button>
				{/each}
			</div>
		{/if}

		{#if error}
			<div class="sidebar-error">{error}</div>
		{/if}
	</aside>

	<!-- Overlay para cerrar sidebar en móvil -->
	{#if panelAbierto && window.innerWidth < 768}
		<div class="sidebar-overlay" on:click={() => panelAbierto = false}></div>
	{/if}

	<!-- Área de chat -->
	<main class="ia-main">
		{#if !conversacionActual}
			<div class="ia-welcome">
				<div class="welcome-card">
					<h1>🤖 ECCSA IA</h1>
					<p>Tu asistente inteligente para consultas internas</p>
					<div class="welcome-hints">
						<h3>¿En qué puedo ayudarte?</h3>
						<ul>
							<li>📋 Consultar reportes de servicio</li>
							<li>📦 Buscar cotizaciones y materiales</li>
							<li>👥 Información de usuarios y permisos</li>
							<li>📊 Análisis de datos y KPIs</li>
							<li>❓ Dudas sobre procesos internos</li>
						</ul>
					</div>
					<button class="btn btn-primary btn-lg" on:click={nuevaConversacion}>💬 Iniciar conversación</button>
				</div>
			</div>
		{:else}
			<div class="ia-chat">
				<!-- Header chat -->
				<header class="chat-header">
					<button class="btn btn-ghost" on:click={() => panelAbierto = true} title="Conversaciones">☰</button>
					<div class="chat-title">
						<h3>{conversacionActual.Titulo}</h3>
						<span class="chat-status">🟢 En línea</span>
					</div>
				</header>

				<!-- Mensajes -->
				<div class="chat-messages" bind:this={messagesContainer}>
					{#if loadingMsg}
						<div class="loading-msgs">Cargando mensajes…</div>
					{:else if mensajes.length === 0}
						<div class="no-msgs">Sin mensajes aún. Escribe abajo para empezar.</div>
					{:else}
						{#each mensajes as m (m.IdMensaje)}
							<div class="message" class:user={m.Rol === 'user'} class:assistant={m.Rol === 'assistant'}>
								<div class="message-bubble">
									{#if m.Rol === 'assistant'}
										<div class="msg-avatar">🤖</div>
									{/if}
									<div class="msg-content">{m.Contenido}</div>
									<div class="msg-time">{formatearFecha(m.FechaCreacion)}</div>
								</div>
							</div>
						{/each}
						{#if enviando}
							<div class="message assistant typing">
								<div class="message-bubble">
									<div class="msg-avatar">🤖</div>
									<div class="msg-typing"><span></span><span></span><span></span></div>
								</div>
							</div>
						{/if}
					{/if}
				</div>

				<!-- Input -->
				<footer class="chat-input">
					<form on:submit={(e) => { e.preventDefault(); enviarMensaje(); }}>
						<div class="input-wrapper">
							<textarea 
								bind:value={nuevoMensaje} 
								placeholder="Escribe tu mensaje… (Shift+Enter = nueva línea, Enter = enviar)"
								rows={1}
								on:keydown={(e) => {
									if (e.key === 'Enter' && !e.shiftKey) {
										e.preventDefault();
										enviarMensaje();
									}
								}}
								disabled={enviando}
							></textarea>
							<button type="submit" class="btn-send" disabled={!nuevoMensaje.trim() || enviando} title="Enviar">➤</button>
						</div>
					</form>
				</footer>
			</div>
		{/if}
	</main>
</div>

<style>
	.ia-page {
		display: flex;
		height: 100vh;
		background: var(--color-background);
	}

	/* Sidebar */
	.ia-sidebar {
		width: 320px;
		min-width: 280px;
		max-width: 400px;
		background: var(--color-surface);
		border-right: 1px solid var(--color-border);
		display: flex;
		flex-direction: column;
		transition: transform 0.25s ease;
		z-index: 100;
	}
	.ia-sidebar.closed { transform: translateX(-100%); }
	.ia-sidebar.open { transform: translateX(0); }

	.sidebar-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		border-bottom: 1px solid var(--color-border);
	}
	.sidebar-header h2 { margin: 0; font-size: 1.1rem; }

	.sidebar-list { flex: 1; overflow: auto; padding: 0.5rem; }
	.sidebar-item {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		width: 100%;
		padding: 0.75rem;
		border: none;
		background: transparent;
		border-radius: 10px;
		cursor: pointer;
		text-align: left;
		gap: 0.5rem;
		transition: background 0.1s;
	}
	.sidebar-item:hover { background: rgba(255,255,255,0.05); }
	.sidebar-item.active { background: rgba(255,107,0,0.15); border: 1px solid var(--color-primary); }
	.item-info { flex: 1; min-width: 0; }
	.item-titulo { font-weight: 600; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.item-fecha { font-size: 0.7rem; color: var(--color-text-muted); margin-top: 0.2rem; }
	.btn-delete { padding: 0.25rem 0.5rem; background: transparent; border: none; color: var(--color-text-muted); cursor: pointer; opacity: 0; transition: opacity 0.1s; }
	.sidebar-item:hover .btn-delete { opacity: 1; }

	.sidebar-empty, .sidebar-loading { padding: 2rem; text-align: center; color: var(--color-text-muted); }
	.sidebar-empty button { margin-top: 1rem; width: 100%; }
	.sidebar-error { padding: 0.75rem; background: rgba(239,68,68,0.1); color: #EF4444; font-size: 0.8rem; margin: 0.5rem; border-radius: 8px; }

	.sidebar-overlay {
		position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 99;
	}

	/* Main chat area */
	.ia-main {
		flex: 1;
		display: flex;
		flex-direction: column;
		background: var(--color-background);
		min-width: 0;
	}

	/* Welcome state */
	.ia-welcome {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
	}
	.welcome-card {
		max-width: 600px;
		width: 100%;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 16px;
		padding: 3rem 2rem;
		text-align: center;
	}
	.welcome-card h1 { margin: 0 0 0.5rem; font-size: 2rem; color: var(--color-primary-light); }
	.welcome-card > p { color: var(--color-text-muted); margin-bottom: 2rem; }
	.welcome-hints { text-align: left; margin: 2rem 0; }
	.welcome-hints h3 { margin: 0 0 1rem; font-size: 1rem; }
	.welcome-hints ul { margin: 0; padding-left: 1.2rem; color: var(--color-text-muted); line-height: 2; }
	.welcome-hints li { list-style: none; }
	.btn-lg { padding: 1rem 2rem; font-size: 1.1rem; }

	/* Chat view */
	.ia-chat {
		flex: 1;
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.chat-header {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
		background: var(--color-surface);
		border-bottom: 1px solid var(--color-border);
		flex-shrink: 0;
	}
	.chat-title { flex: 1; }
	.chat-title h3 { margin: 0; font-size: 1rem; }
	.chat-status { font-size: 0.7rem; color: var(--color-text-muted); }

	.chat-messages {
		flex: 1;
		overflow-y: auto;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.loading-msgs, .no-msgs { text-align: center; color: var(--color-text-muted); padding: 2rem; }

	.message {
		display: flex;
		width: 100%;
		animation: fadeIn 0.2s ease;
	}
	.message.user { justify-content: flex-end; }
	.message.assistant { justify-content: flex-start; }
	@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

	.message-bubble {
		max-width: 75%;
		padding: 0.75rem 1rem;
		border-radius: 18px;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}
	.message.user .message-bubble {
		background: var(--color-primary);
		color: white;
		border-bottom-right-radius: 4px;
	}
	.message.assistant .message-bubble {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		color: var(--color-text);
		border-bottom-left-radius: 4px;
	}
	.message.assistant.typing .message-bubble { min-width: 80px; }

	.msg-avatar { font-size: 1.2rem; margin-right: 0.5rem; }
	.msg-content { 
		line-height: 1.5; 
		white-space: pre-wrap; 
		word-wrap: break-word;
	}
	.msg-time { 
		font-size: 0.65rem; 
		opacity: 0.6; 
		text-align: right;
		margin-top: 0.25rem;
	}
	.message.user .msg-time { color: rgba(255,255,255,0.7); }
	.msg-typing { display: flex; gap: 3px; padding: 0.25rem 0; }
	.msg-typing span {
		width: 8px; height: 8px; background: var(--color-text-muted); border-radius: 50%;
		animation: typing 1.4s infinite ease-in-out;
	}
	.msg-typing span:nth-child(2) { animation-delay: 0.2s; }
	.msg-typing span:nth-child(3) { animation-delay: 0.4s; }
	@keyframes typing { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }

	/* Input */
	.chat-input {
		padding: 1rem;
		background: var(--color-surface);
		border-top: 1px solid var(--color-border);
		flex-shrink: 0;
	}
	.input-wrapper {
		display: flex;
		gap: 0.5rem;
		align-items: flex-end;
		max-width: 100%;
	}
	.input-wrapper textarea {
		flex: 1;
		min-height: 44px;
		max-height: 150px;
		padding: 0.75rem 1rem;
		border: 1px solid var(--color-border);
		border-radius: 24px;
		background: var(--color-background);
		color: var(--color-text);
		font-family: inherit;
		font-size: 0.95rem;
		line-height: 1.5;
		resize: none;
		transition: border-color 0.15s;
	}
	.input-wrapper textarea:focus { outline: none; border-color: var(--color-primary); }
	.input-wrapper textarea::placeholder { color: var(--color-text-muted); }
	.btn-send {
		width: 44px; height: 44px;
		border-radius: 50%;
		background: var(--color-primary);
		color: white;
		border: none;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.2rem;
		transition: transform 0.1s, background 0.15s;
		flex-shrink: 0;
	}
	.btn-send:hover:not(:disabled) { background: var(--color-primary-light); transform: scale(1.05); }
	.btn-send:disabled { opacity: 0.4; cursor: not-allowed; }

	/* Responsive */
	@media (max-width: 767px) {
		.ia-sidebar { position: fixed; top: 0; left: 0; bottom: 0; z-index: 200; }
		.ia-sidebar:not(.open) { transform: translateX(-100%); }
		.chat-header .btn-ghost { display: flex; }
		.message-bubble { max-width: 85%; }
	}
	@media (min-width: 768px) {
		.chat-header .btn-ghost { display: none; }
	}
</style>