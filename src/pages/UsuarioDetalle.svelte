<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { api } from '$lib/api.js';
	import PasswordInput from '../components/PasswordInput.svelte';

	// id viene de la ruta /usuarios/:id (micro-router, modo runes -> $props)
	let { id } = $props();

	// Grupos de permisos idénticos a PERM_GROUPS del HUB (views/administrador_usuarios.py)
	const PERM_GROUPS = {
		'📊 Administración': [
			['AccesoConfiguracion', 'Configuración (Cambio PW)'],
			['AccesoUsuarios', 'Administrador de Usuarios'],
			['AccesoAppConfig', 'AppConfig ⚙️'],
			['AccesoEdicionBD', 'Edición BD 🗄️'],
			['Notificaciones', 'Notificaciones Push 🔔'],
			['AccesoConfigurarCorreo', 'Configurar Correo 📧'],
			['AccesoConfigAI', 'Configuración IA 🤖']
		],
		'📋 Operativo': [
			['AccesoReportes', 'Reportes de Servicio'],
			['AccesoRegistroReportes', 'Registro de Reportes'],
			['AccesoCotizacionesReportes', 'Cotizaciones Serv/Proy'],
			['AccesoClientes', 'Clientes'],
			['AccesoRegistroKilometros', 'Registro Kilómetros'],
			['AccesoAutomoviles', 'Automóviles']
		],
		'💰 Financiero': [
			['AccesoCotizaciones', 'Cotizaciones Materiales'],
			['AccesoCalculo', 'Cálculos 🧮'],
			['AccesoProveedores', 'Proveedores 🏭'],
			['AccesoOC', 'Órdenes de Compra 🛒'],
			['AccesoNominas', 'Nóminas 💵'],
			['AccesoInventario', 'Inventario 📦']
		],
		'⏰ Tiempo': [
			['AccesoVacaciones', 'Vacaciones ✈️'],
			['AccesoMisVacaciones', 'Mis Vacaciones 🏖️'],
			['AccesoHorasExtras', 'Horas Extras ⏰'],
			['AccesoMisHorasExtras', 'Mis Horas Extras 🕒']
		],
		'⛽ OxxoGas': [
			['AccesoOxxoGas', 'Gmail OxxoGas ⛽'],
			['AccesoValesOxxoGas', 'Vales OxxoGas 🚗'],
			['AccesoRegistroTicketOxxoGas', 'Ticket OxxoGas 🎫'],
			['AccesoSolicitarVales', 'Solicitar Vales QR 📲'],
			['AccesoAdminVales', 'Admin Vales QR ✅'],
			['AccesoConfigOxxogas', 'Config OxxoGas ⚙️']
		],
		'🔧 Otros': [
			['AccesoVM', 'Programas VM'],
			['AccesoTelegram', 'Telegram 📱'],
			['AccesoDeteccionRed', 'Detección de Red 📡'],
			['AccesoPdfConfig', 'Guardado PDFs 📁']
		]
	};

	let loading = $state(true);
	let error = $state('');
	let msg = $state('');
	let busy = $state(false);

	let nombre = $state('');
	let email = $state('');
	let curpRfc = $state('');
	let password = $state('');
	let fechaIngreso = $state('');
	let activo = $state(true);
	let accesos = $state({});
	let isSelf = $state(false);

	function apiHeaders() {
		return { 'Content-Type': 'application/json', ...auth.authHeader() };
	}

	function tieneAcceso() {
		try {
			const raw = localStorage.getItem('admon_user');
			const u = raw ? JSON.parse(raw) : null;
			return !!(u && u.acceso_usuarios);
		} catch {
			return false;
		}
	}

	function myEmail() {
		try {
			const raw = localStorage.getItem('admon_user');
			const u = raw ? JSON.parse(raw) : null;
			return (u && u.email ? String(u.email) : '').trim().toLowerCase();
		} catch {
			return '';
		}
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
		try {
			// GET con caché offline: red primero, si no hay red sirve el
			// detalle cacheado por el prefetch (últimos 10 usuarios).
			const d = await api.get(`/users/${id}`);
			nombre = d.nombre || '';
			email = d.email || '';
			curpRfc = d.curp_rfc || '';
			password = d.password || '';
			fechaIngreso = d.fecha_ingreso || '';
			activo = !!d.activo;
			const a = {};
			for (const g of Object.values(PERM_GROUPS)) for (const [k] of g) a[k] = !!d[k];
			accesos = a;
			isSelf = (email || '').trim().toLowerCase() === myEmail();
		} catch (e) {
			console.error('Error cargando usuario:', e);
			error = e.message === 'Sesión expirada' ? e.message : `No se pudo cargar: ${e.message || 'sin detalle'}`;
		} finally {
			loading = false;
		}
	});

	async function guardar() {
		msg = '';
		error = '';
		if (!nombre.trim() || !email.trim() || !password.trim()) {
			error = 'Nombre, correo y contraseña son obligatorios.';
			return;
		}
		busy = true;
		try {
			const res = await fetch(`/api/users/${id}`, {
				method: 'PUT',
				headers: apiHeaders(),
				body: JSON.stringify({
					nombre: nombre.trim(),
					email: email.trim(),
					password,
					activo,
					fecha_ingreso: fechaIngreso || null,
					curp_rfc: curpRfc.trim(),
					accesos
				})
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al actualizar.');
			msg = '✅ Usuario actualizado.';
		} catch (e) {
			error = e.message || 'Error al actualizar.';
		} finally {
			busy = false;
		}
	}

	async function eliminar() {
		if (isSelf) return;
		if (!confirm(`¿Eliminar al usuario "${nombre}"?`)) return;
		msg = '';
		error = '';
		busy = true;
		try {
			const res = await fetch(`/api/users/${id}`, { method: 'DELETE', headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al eliminar.');
			navigate('/usuarios', { replace: true });
		} catch (e) {
			error = e.message || 'Error al eliminar.';
			busy = false;
		}
	}
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/usuarios')} title="Volver">⬅️</button>
		<h1>✏️ {nombre || 'Usuario'}</h1>
	</div>

	{#if loading}
		<div class="empty">Cargando…</div>
	{:else if error && !nombre}
		<div class="card"><p style="color: var(--color-danger); margin: 0;">{error}</p></div>
	{:else}
		<div class="card" style="margin-bottom: 0.75rem;">
			<div class="card-title">📝 Datos</div>
			<div class="field">
				<label for="ud-nombre">Nombre completo:</label>
				<input id="ud-nombre" class="input" bind:value={nombre} />
			</div>
			<div class="field">
				<label for="ud-email">Correo electrónico:</label>
				<input id="ud-email" type="email" class="input" bind:value={email} />
			</div>
			<div class="field">
				<label for="ud-curp">CURP / RFC:</label>
				<input id="ud-curp" class="input" placeholder="Ej: PEGC850101ABC" bind:value={curpRfc} />
			</div>
			<div class="field">
				<label for="ud-pw">Contraseña:</label>
				<PasswordInput id="ud-pw" autocomplete="new-password" bind:value={password} />
			</div>
			<div class="field">
				<label for="ud-fecha">Fecha de ingreso:</label>
				<input id="ud-fecha" type="date" class="input" bind:value={fechaIngreso} />
			</div>
			<label class="check"><input type="checkbox" bind:checked={activo} /> Usuario activo</label>
		</div>

		<div class="card" style="margin-bottom: 0.75rem;">
			<div class="card-title">🔑 Permisos</div>
			{#each Object.entries(PERM_GROUPS) as [grupo, perms]}
				<p style="font-weight: 700; font-size: 0.85rem; margin: 0.75rem 0 0.35rem;">{grupo}</p>
				{#each perms as [key, label]}
					<label class="check"><input type="checkbox" bind:checked={accesos[key]} /> {label}</label>
				{/each}
			{/each}
		</div>

		{#if error}
			<div class="msg err">{error}</div>
		{/if}
		{#if msg}
			<div class="msg ok">{msg}</div>
		{/if}

		<button class="btn btn-primary btn-block" on:click={guardar} disabled={busy}>
			{busy ? 'Guardando…' : '💾 Guardar cambios'}
		</button>
		{#if isSelf}
			<p class="hint" style="margin-top: 0.75rem;">ℹ️ No puedes eliminar tu propia cuenta desde aquí.</p>
		{:else}
			<button class="btn btn-danger btn-block" style="margin-top: 0.5rem;" on:click={eliminar} disabled={busy}>
				🚨 Eliminar usuario
			</button>
		{/if}
	{/if}
</div>

<style>
	.card-title { font-weight: 700; font-size: 1rem; margin-bottom: 0.25rem; }
	.msg { padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 0.75rem; }
	.msg.err { background: rgba(239,68,68,0.1); color: #EF4444; }
	.msg.ok { background: rgba(34,197,94,0.1); color: #22C55E; }
	.check { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; margin-bottom: 0.5rem; cursor: pointer; }
	.check input { width: 1.1rem; height: 1.1rem; }
	.hint { font-size: 0.8rem; color: var(--color-text-muted); }
	.card { margin-bottom: 0.75rem; }
</style>
