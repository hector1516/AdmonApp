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

	// Teléfono / MAC: se guarda en HUB_NetworkDevices (la tabla del escáner de
	// red 📡 que mide entradas y salidas de la oficina), vinculada por IdUsuario.
	let macTel = $state('');
	let macNombre = $state('');
	let tel = $state(null); // estado del dispositivo + presencia (AQUI/FUERA)
	let busyMac = $state(false);
	let msgMac = $state('');
	let errMac = $state('');

	function fmtFecha(iso) {
		if (!iso) return '—';
		const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
		if (m) return `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}`;
		return '—';
	}

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
			// MAC del teléfono (HUB_NetworkDevices); si falla no bloquea la ficha
			try {
				tel = await api.get(`/users/${id}/telefono`);
				macTel = tel?.mac || '';
				macNombre = tel?.nombre_dispositivo || '';
			} catch (e2) {
				console.error('Error cargando MAC:', e2);
			}
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

	async function guardarMac() {
		msgMac = '';
		errMac = '';
		busyMac = true;
		try {
			const res = await fetch(`/api/users/${id}/telefono`, {
				method: 'PUT',
				headers: apiHeaders(),
				body: JSON.stringify({ mac: macTel.trim(), nombre_dispositivo: macNombre.trim() })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al guardar la MAC.');
			tel = data;
			macTel = data.mac || '';
			macNombre = data.nombre_dispositivo || '';
			msgMac = data.mac
				? '✅ MAC vinculada. El escáner 📡 ya puede medir sus entradas y salidas.'
				: '✅ Teléfono desvinculado (el historial se conserva).';
		} catch (e) {
			errMac = e.message || 'Error al guardar la MAC.';
		} finally {
			busyMac = false;
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
			<div class="card-title">📱 MAC del teléfono</div>
			<p class="hint" style="margin: 0 0 0.6rem;">
				📡 Detección de Red: con esta MAC el escáner mide las <b>entradas y salidas</b> de la
				oficina. Los iPhone con “dirección Wi-Fi privada” rotan su MAC: si deja de detectarse,
				vuelve a anotarla aquí.
			</p>
			<div class="field">
				<label for="ud-mac">MAC del celular:</label>
				<input
					id="ud-mac"
					class="input"
					placeholder="EE:E2:FD:A3:43:EC"
					bind:value={macTel}
					on:blur={() => (macTel = macTel.trim().toUpperCase())}
				/>
			</div>
			<div class="field">
				<label for="ud-mac-nombre">Nombre del dispositivo (opcional):</label>
				<input id="ud-mac-nombre" class="input" placeholder="Ej: iPhone Héctor" bind:value={macNombre} />
			</div>

			{#if tel && tel.id_dispositivo}
				<div class="tel-estado">
					{#if tel.estado === 'AQUI'}
						<span class="tel-chip tel-aqui">🟢 En la oficina</span>
					{:else}
						<span class="tel-chip">⚪ Fuera</span>
					{/if}
					{#if tel.ultimo_evento}
						<span class="tel-chip">
							{tel.ultimo_evento.tipo === 'ENTRADA' ? '⬅️ Última entrada' : '➡️ Última salida'}:
							{fmtFecha(tel.ultimo_evento.fecha)}
						</span>
					{/if}
					{#if tel.ultima_vez_en_red}
						<span class="tel-chip">📶 Visto: {fmtFecha(tel.ultima_vez_en_red)}</span>
					{/if}
				</div>
			{:else}
				<p class="hint" style="margin: 0 0 0.6rem;">➕ Sin MAC registrada — anóntala para empezar a medir su asistencia.</p>
			{/if}

			{#if errMac}<div class="msg err">{errMac}</div>{/if}
			{#if msgMac}<div class="msg ok">{msgMac}</div>{/if}

			<button class="btn btn-secondary btn-block" on:click={guardarMac} disabled={busyMac}>
				{busyMac ? 'Guardando…' : macTel.trim() ? '💾 Guardar MAC' : '💾 Desvincular teléfono'}
			</button>
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
	.tel-estado { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.6rem; }
	.tel-chip {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		font-size: 0.75rem;
		padding: 0.25rem 0.55rem;
		border-radius: 999px;
		background: rgba(255, 255, 255, 0.06);
		color: var(--color-text-muted);
	}
	.tel-aqui { background: rgba(34, 197, 94, 0.14); color: #22C55E; }
	.card { margin-bottom: 0.75rem; }
</style>
