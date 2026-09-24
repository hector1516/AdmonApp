<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';

	// --- Cambiar contraseña ---
	let actual = $state('');
	let nueva = $state('');
	let confirma = $state('');
	let pwMsg = $state('');
	let pwErr = $state('');
	let pwBusy = $state(false);

	// --- Instalar app ---
	let isIos = $state(false);
	let isStandalone = $state(false);
	let canInstall = $state(false);
	let deferredPrompt = $state(null);

	// --- Aviso push (solo admin) ---
	let isAdmin = $state(false);
	let avTitle = $state('');
	let avBody = $state('');
	let avAll = $state(true);
	let avUsers = $state([]);
	let avSelected = $state([]);
	let avBusy = $state(false);
	let avMsg = $state('');
	let avErr = $state('');

	// --- Dispositivo ---
	let devIp = $state('...');

	function apiHeaders() {
		return { 'Content-Type': 'application/json', ...auth.authHeader() };
	}

	// Info del equipo (equivalente a $lib/device de Field, en línea)
	function getBrowser() {
		const ua = navigator.userAgent || '';
		if (/Edg\//.test(ua)) return 'Edge';
		if (/Chrome\//.test(ua)) return 'Chrome';
		if (/Safari\//.test(ua) && !/Chrome\//.test(ua)) return 'Safari';
		if (/Firefox\//.test(ua)) return 'Firefox';
		return 'Otro';
	}
	function getOS() {
		const ua = navigator.userAgent || '';
		if (/Android/.test(ua)) return 'Android';
		if (/iPhone|iPad|iPod/.test(ua)) return 'iOS';
		if (/Windows/.test(ua)) return 'Windows';
		if (/Macintosh/.test(ua)) return 'macOS';
		if (/Linux/.test(ua)) return 'Linux';
		return 'Otro';
	}
	function getDeviceType() {
		const ua = navigator.userAgent || '';
		if (/Mobi|Android|iPhone|iPod/.test(ua)) return 'Móvil';
		if (/iPad/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return 'Tableta';
		return 'Escritorio';
	}

	onMount(async () => {
		if (!auth.isLoggedIn()) {
			navigate('/login', { replace: true });
			return;
		}
		try {
			const raw = localStorage.getItem('admon_user');
			const u = raw ? JSON.parse(raw) : null;
			isAdmin = !!(u && u.acceso_usuarios);
		} catch {
			isAdmin = false;
		}
		const ua = navigator.userAgent || '';
		isIos = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
		isStandalone =
			(window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) ||
			navigator.standalone === true;
		window.addEventListener('beforeinstallprompt', (e) => {
			e.preventDefault();
			deferredPrompt = e;
			canInstall = true;
		});
		try {
			const res = await fetch('/api/dispositivo/ip', { headers: auth.authHeader() });
			devIp = res.ok ? (await res.json()).ip || '?' : 'sin conexión';
		} catch {
			devIp = 'sin conexión';
		}
		if (isAdmin) {
			try {
				const res = await fetch('/api/users', { headers: auth.authHeader() });
				if (res.ok) avUsers = await res.json();
			} catch {}
		}
	});

	async function installApp() {
		if (deferredPrompt) {
			deferredPrompt.prompt();
			await deferredPrompt.userChoice.catch(() => {});
			deferredPrompt = null;
			canInstall = false;
		}
	}

	function toggleAvUser(id) {
		avSelected = avSelected.includes(id) ? avSelected.filter((x) => x !== id) : [...avSelected, id];
	}

	async function sendAviso() {
		avMsg = '';
		avErr = '';
		if (!avTitle.trim() || !avBody.trim()) {
			avErr = 'Escribe título y mensaje.';
			return;
		}
		if (!avAll && avSelected.length === 0) {
			avErr = 'Selecciona al menos un usuario o marca Todos.';
			return;
		}
		avBusy = true;
		try {
			const res = await fetch('/api/push/send', {
				method: 'POST',
				headers: apiHeaders(),
				body: JSON.stringify({ title: avTitle.trim(), body: avBody.trim(), all: avAll, user_ids: avAll ? [] : avSelected })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'No se pudo enviar.');
			avMsg = `✅ Aviso enviado a ${data.sent} usuario(s).`;
			avTitle = '';
			avBody = '';
		} catch (e) {
			avErr = e.message || 'No se pudo enviar.';
		} finally {
			avBusy = false;
		}
	}

	async function changePassword() {
		pwMsg = '';
		pwErr = '';
		if (!actual || !nueva || !confirma) {
			pwErr = 'Completa los tres campos.';
			return;
		}
		if (nueva !== confirma) {
			pwErr = 'La nueva contraseña y su confirmación no coinciden.';
			return;
		}
		pwBusy = true;
		try {
			const res = await fetch('/api/auth/change-password', {
				method: 'POST',
				headers: apiHeaders(),
				body: JSON.stringify({ actual, nueva })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'No se pudo cambiar la contraseña.');
			pwMsg = '✅ Contraseña actualizada.';
			actual = '';
			nueva = '';
			confirma = '';
		} catch (e) {
			pwErr = e.message || 'No se pudo cambiar la contraseña.';
		} finally {
			pwBusy = false;
		}
	}
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/dashboard')} title="Volver">⬅️</button>
		<h1>⚙️ Configuración</h1>
	</div>

	<div class="card">
		<div class="card-title">📲 Instalar app</div>
		{#if isStandalone}
			<p class="hint">✅ App instalada. Las notificaciones push funcionan en este equipo.</p>
		{:else if canInstall}
			<p class="hint">Instala Admon para notificaciones push y acceso directo.</p>
			<button class="btn btn-primary btn-block" on:click={installApp}>📲 Instalar Admon</button>
		{:else if isIos}
			<p class="hint">En iPhone: toca <strong>Compartir</strong> (cuadro con ↑) → <strong>Añadir a pantalla de inicio</strong>. Solo instalada llegan las notificaciones.</p>
		{:else}
			<p class="hint">Desde el menú del navegador usa <strong>Instalar app / Añadir a pantalla de inicio</strong> para notificaciones push.</p>
		{/if}
	</div>

	{#if isAdmin}
		<div class="card">
			<div class="card-title">📣 Enviar aviso push</div>
			<p class="hint">Llega a los equipos con la app instalada y notificaciones aceptadas.</p>
			<div class="field">
				<label for="avTitle">Título:</label>
				<input id="avTitle" class="input" maxlength="120" placeholder="Ej. Aviso importante" bind:value={avTitle} />
			</div>
			<div class="field">
				<label for="avBody">Mensaje:</label>
				<textarea id="avBody" class="input" rows="3" maxlength="500" placeholder="Texto del aviso..." bind:value={avBody}></textarea>
			</div>
			<label class="check"><input type="checkbox" bind:checked={avAll} /> Todos los usuarios activos</label>
			{#if !avAll}
				<div class="userlist">
					{#each avUsers as u (u.id)}
						<label class="check"><input type="checkbox" checked={avSelected.includes(u.id)} on:change={() => toggleAvUser(u.id)} /> {u.nombre}</label>
					{/each}
				</div>
			{/if}
			{#if avErr}
				<div class="msg err">{avErr}</div>
			{/if}
			{#if avMsg}
				<div class="msg ok">{avMsg}</div>
			{/if}
			<button class="btn btn-primary btn-block" on:click={sendAviso} disabled={avBusy}>
				{avBusy ? 'Enviando...' : '📣 Enviar aviso'}
			</button>
		</div>
	{/if}

	<div class="card">
		<div class="card-title">🔑 Cambiar contraseña</div>
		<div class="field">
			<label for="pwActual">Contraseña actual:</label>
			<input id="pwActual" type="password" class="input" autocomplete="current-password" bind:value={actual} />
		</div>
		<div class="field">
			<label for="pwNueva">Nueva contraseña (mínimo 6 caracteres):</label>
			<input id="pwNueva" type="password" class="input" autocomplete="new-password" bind:value={nueva} />
		</div>
		<div class="field">
			<label for="pwConfirma">Confirmar nueva contraseña:</label>
			<input id="pwConfirma" type="password" class="input" autocomplete="new-password" bind:value={confirma} />
		</div>
		{#if pwErr}
			<div class="msg err">{pwErr}</div>
		{/if}
		{#if pwMsg}
			<div class="msg ok">{pwMsg}</div>
		{/if}
		<button class="btn btn-primary btn-block" on:click={changePassword} disabled={pwBusy}>
			{pwBusy ? 'Guardando...' : '💾 Guardar nueva contraseña'}
		</button>
	</div>

	<div class="card">
		<div class="card-title">📱 Este dispositivo</div>
		<div class="dev-row"><span>Navegador</span><strong>{getBrowser()}</strong></div>
		<div class="dev-row"><span>Sistema operativo</span><strong>{getOS()}</strong></div>
		<div class="dev-row"><span>Tipo de dispositivo</span><strong>{getDeviceType()}</strong></div>
		<div class="dev-row"><span>Resolución pantalla</span><strong>{window.screen.width}x{window.screen.height}</strong></div>
		<div class="dev-row"><span>Idioma</span><strong>{navigator.language}</strong></div>
		<div class="dev-row"><span>Zona horaria</span><strong>{Intl.DateTimeFormat().resolvedOptions().timeZone}</strong></div>
		<div class="dev-row"><span>IP</span><strong>{devIp}</strong></div>
		<div class="dev-row col"><span>User Agent</span><code>{navigator.userAgent}</code></div>
	</div>
</div>

<style>
	.card-title { font-weight: 700; font-size: 1rem; margin-bottom: 0.25rem; }
	.hint { font-size: 0.8rem; color: var(--color-text-muted); margin: 0 0 0.5rem; }
	.msg { padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 0.75rem; }
	.msg.err { background: rgba(239,68,68,0.1); color: #EF4444; }
	.msg.ok { background: rgba(34,197,94,0.1); color: #22C55E; }
	.dev-row { display: flex; justify-content: space-between; gap: 1rem; font-size: 0.8rem; padding: 0.45rem 0; border-top: 1px solid rgba(255,255,255,0.05); }
	.dev-row span { color: var(--color-text-muted); flex-shrink: 0; }
	.dev-row strong { font-weight: 600; text-align: right; word-break: break-word; }
	.dev-row.col { flex-direction: column; gap: 0.25rem; }
	.dev-row code { font-size: 0.68rem; color: var(--color-text-muted); word-break: break-all; font-family: monospace; }
	.check { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; margin-bottom: 0.5rem; cursor: pointer; }
	.check input { width: 1.1rem; height: 1.1rem; }
	.userlist { max-height: 180px; overflow-y: auto; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 0.75rem; }
	.card { margin-bottom: 0.75rem; }
</style>
