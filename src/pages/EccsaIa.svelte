<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';

	// ECCSA IA (Edwin Jarvis) - CLON EXACTO del HUB views/edwin_jarvis.py
	// Disponible para TODOS los usuarios logueados (sin permiso especial)
	// FIFO: máx 10 conversaciones por usuario
	// 3 Tools: execute_query, send_quote_pdf, send_service_reports

	let conversaciones = $state([]);
	let mensajes = $state([]);
	let conversacionActual = $state(null);
	let nuevoMensaje = $state('');
	let enviando = $state(false);
	let loading = $state(true);
	let loadingMsg = $state(false);
	let error = $state('');

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
				await seleccionarConversacion(conversaciones[0].Id);
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
			conversacionActual = conversaciones.find(c => c.Id === id) || null;
		} catch (e) {
			error = e.message === 'Sesión expirada' ? e.message : 'No se pudo cargar mensajes.';
		} finally {
			loadingMsg = false;
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
			if (data.Id) {
				await seleccionarConversacion(data.Id);
			}
		} catch (e) {
			error = e.message || 'Error al crear conversación.';
		}
	}

	async function eliminarConversacion(id) {
		if (!confirm('¿Eliminar esta conversación y todos sus mensajes?')) return;
		error = '';
		try {
			const res = await fetch(`/api/ia/conversaciones/${id}`, { method: 'DELETE', headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al eliminar.');
			if (conversacionActual?.Id === id) {
				conversacionActual = null;
				mensajes = [];
			}
			await cargarConversaciones();
		} catch (e) {
			error = e.message || 'Error al eliminar.';
		}
	}

	async function enviarMensaje() {
		if (!nuevoMensaje.trim() || !conversacionActual || enviando) return;
		const texto = nuevoMensaje.trim();
		nuevoMensaje = '';
		enviando = true;
		error = '';

		// Optimistic UI: agregar mensaje usuario inmediatamente
		const msgUsuario = {
			Id: Date.now(),
			Role: 'user',
			Contenido: texto,
			FechaRegistro: new Date().toISOString()
		};
		mensajes = [...mensajes, msgUsuario];

		try {
			const res = await fetch(`/api/ia/conversaciones/${conversacionActual.Id}/mensajes`, {
				method: 'POST',
				headers: apiHeaders(),
				body: JSON.stringify({ contenido: texto })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al enviar.');

			// Reemplazar con respuesta real (incluye respuesta del assistant)
			mensajes = data.mensajes || [];

			// Actualizar título si es nueva conversación
			if (conversacionActual.Titulo === 'Nueva conversación' && data.titulo) {
				conversacionActual.Titulo = data.titulo;
				const idx = conversaciones.findIndex(c => c.Id === conversacionActual.Id);
				if (idx >= 0) conversaciones[idx].Titulo = data.titulo;
			}
		} catch (e) {
			error = e.message || 'Error al enviar mensaje.';
			// Remover mensaje optimista en error
			mensajes = mensajes.filter(m => m.Id !== msgUsuario.Id);
		} finally {
			enviando = false;
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

	onMount(async () => {
		if (!auth.isLoggedIn()) {
			navigate('/login', { replace: true });
			return;
		}
		await cargarConversaciones();
	});
</script>

<div class="ia-page">
	<!-- Sidebar conversaciones -->
	<aside class="ia-sidebar">
		<div class="sidebar-header">
			<h2>🤖 ECCSA IA</h2>
			<button class="btn btn-primary btn-sm" on:click={nuevaConversacion} title="Nueva conversación">➕ Nueva</button>
		</div>

		{#if loading}
			<div class="sidebar-loading">Cargando…</div>
		{:else if conversaciones.length === 0}
			<div class="sidebar-empty">
				<p>Sin conversaciones aún</p>
				<button class="btn btn-primary btn-sm" on:click={nuevaConversacion} style="width: 100%;">➕ Iniciar chat</button>
			</div>
		{:else}
			<div class="sidebar-list">
				{#each conversaciones as c (c.Id)}
<button 
					class="sidebar-item" 
					class:active={conversacionActual?.Id === c.Id}
					on:click={() => seleccionarConversacion(c.Id)}
				>
					<div class="item-info">
						<div class="item-titulo">{c.Titulo || 'Nueva conversación'}</div>
						<div class="item-fecha">{formatearFecha(c.FechaCreacion)}</div>
					</div>
					<span class="btn-delete" on:click={(e) => { e.stopPropagation(); eliminarConversacion(c.Id); }} title="Eliminar">🗑️</span>
				</button>
				{/each}
			</div>
		{/if}

		{#if error}
			<div class="sidebar-error">{error}</div>
		{/if}
	</aside>

	<!-- Área de chat -->
	<main class="ia-main">
		{#if !conversacionActual}
			<div class="ia-welcome">
				<div class="welcome-card">
					<h1>🤖 ECCSA IA</h1>
					<p>Tu asistente inteligente para consultas de datos, generación de PDFs y envío de correos.</p>
					<div class="welcome-hints">
						<h3>¿En qué puedo ayudarte?</h3>
						<ul>
							<li>📦 Cotizaciones y partidas de materiales</li>
							<li>📋 Reportes de servicio técnico</li>
							<li>👥 Clientes y kilómetros recorridos</li>
							<li>💡 Sugerencia de claves SAT</li>
							<li>📧 Envío de PDFs por correo</li>
						</ul>
					</div>
					<button class="btn btn-primary btn-lg" on:click={nuevaConversacion}>💬 Iniciar conversación</button>
				</div>
			</div>
		{:else}
			<div class="ia-chat">
				<!-- Header chat -->
				<header class="chat-header">
					<h3>{conversacionActual.Titulo}</h3>
					<span class="chat-status">🟢 En línea</span>
				</header>

				<!-- Mensajes -->
				<div class="chat-messages" bind:this={messagesContainer}>
					{#if loadingMsg}
						<div class="loading-msgs">Cargando mensajes…</div>
					{:else if mensajes.length === 0}
						<div class="no-msgs">
							<div class="welcome-bubble">
								<div class="chat-sender-label">ECCSA IA</div>
								¡Hola! Soy <b>ECCSA IA</b>, tu asistente virtual inteligente de <b>ECCSA Automation</b>.<br><br>
								Tengo acceso a la base de datos para ayudarte con:<br>
								• 📦 Cotizaciones y partidas de materiales<br>
								• 📋 Reportes de servicio técnico<br>
								• 👥 Clientes y kilómetros recorridos<br><br>
								También puedo <b>sugerir claves SAT</b> y <b>enviar PDFs por correo</b>.<br><br>
								¿En qué puedo ayudarte hoy?
							</div>
						</div>
					{:else}
						{#each mensajes as m (m.Id)}
							<div class="message" class:user={m.Role === 'user'} class:assistant={m.Role === 'model' || m.Role === 'assistant'}>
								<div class="message-bubble">
									{#if m.Role === 'model' || m.Role === 'assistant'}
										<div class="msg-avatar">🤖</div>
									{/if}
									<div class="msg-content">{m.Contenido}</div>
									<div class="msg-time">{formatearFecha(m.FechaRegistro)}</div>
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
								placeholder="Escribe tu pregunta a ECCSA IA… (Shift+Enter = nueva línea, Enter = enviar)"
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
	}

	.sidebar-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		border-bottom: 1px solid var(--color-border);
	}
	.sidebar-header h2 { margin: 0; font-size: 1.1rem; }
	.sidebar-header .btn-sm { padding: 0.4rem 0.75rem; font-size: 0.8rem; }

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
	.btn-delete { padding: 0.25rem 0.5rem; background: transparent; border: none; color: var(--color-text-muted); cursor: pointer; opacity: 0; transition: opacity 0.1s; font-size: 1rem; }
	.sidebar-item:hover .btn-delete { opacity: 1; }

	.sidebar-empty, .sidebar-loading { padding: 2rem; text-align: center; color: var(--color-text-muted); }
	.sidebar-empty button { margin-top: 1rem; width: 100%; }
	.sidebar-error { padding: 0.75rem; background: rgba(239,68,68,0.1); color: #EF4444; font-size: 0.8rem; margin: 0.5rem; border-radius: 8px; }

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
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		background: var(--color-surface);
		border-bottom: 1px solid var(--color-border);
		flex-shrink: 0;
	}
	.chat-header h3 { margin: 0; font-size: 1rem; }
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

	.welcome-bubble {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 18px 18px 18px 2px;
		padding: 1rem 1.25rem;
		max-width: 80%;
		margin: 0 auto;
		color: var(--color-text);
		font-family: inherit;
		line-height: 1.6;
	}
	.welcome-bubble .chat-sender-label {
		font-size: 0.75rem;
		color: #94A3B8;
		margin-bottom: 0.5rem;
		font-weight: 600;
	}

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
</style>