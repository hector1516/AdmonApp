<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { api } from '$lib/api.js';

	let usuarios = $state([]);
	let loading = $state(true);
	let error = $state('');
	// 📷 Avatar por usuario: {id → blob URL}. Solo se pide la foto de quienes
	// tienen, en paralelo, y se cachea en la sesión para no repetir la descarga
	// cada vez que se vuelve a la lista.
	let avatares = $state({});

	function iniciales(nombre) {
		const partes = String(nombre || '').trim().split(/\s+/).filter(Boolean);
		if (!partes.length) return '👤';
		return ((partes[0][0] || '') + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
	}

	async function cargarAvatares() {
		await Promise.all(
			usuarios
				.filter((u) => u.tiene_foto && !avatares[u.id])
				.map(async (u) => {
					try {
						const r = await fetch(`/api/users/${u.id}/foto`, { headers: auth.authHeader() });
						if (!r.ok) return;
						const blob = await r.blob();
						avatares = { ...avatares, [u.id]: URL.createObjectURL(blob) };
					} catch {
						// sin conexión o sin foto: se queda el avatar de iniciales
					}
				})
		);
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
			// GET con caché offline: red primero, si no hay red sirve los
			// últimos usuarios cacheados por el prefetch.
			usuarios = (await api.get('/users')) || [];
		} catch (e) {
			if (e.message === 'Sesión expirada') {
				error = e.message;
			} else {
				error = e.message || 'No se pudo cargar. Revisa tu conexión.';
			}
		} finally {
			loading = false;
		}
		// Las fotos se piden después de pintar la lista: la lista aparece ya
		// con iniciales y las fotos se van poniendo conforme llegan.
		await cargarAvatares();
	});
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/dashboard')} title="Volver">⬅️</button>
		<h1>👥 Administrador de usuarios</h1>
	</div>

	<div class="card" style="margin-bottom: 0.75rem;">
		<p style="color: var(--color-text-muted); font-size: 0.8rem; text-transform: uppercase; margin: 0 0 0.25rem;">Total usuarios</p>
		<p style="font-size: 1.5rem; font-weight: 700; margin: 0;">{usuarios.length}</p>
	</div>

	{#if loading}
		<div class="empty">Cargando…</div>
	{:else if error}
		<div class="card"><p style="color: var(--color-danger); margin: 0;">{error}</p></div>
	{:else if usuarios.length === 0}
		<div class="empty">No hay usuarios registrados.</div>
	{:else}
		<div class="list">
			{#each usuarios as u (u.id)}
				<button class="list-card" on:click={() => navigate(`/usuarios/${u.id}`)}>
					<div class="avatar" class:mini={u.activo === false}>
						{#if avatares[u.id]}
							<img src={avatares[u.id]} alt="" />
						{:else}
							<span>{iniciales(u.nombre)}</span>
						{/if}
					</div>
					<div style="flex: 1; min-width: 0;">
						<div style="font-weight: 600;">{u.nombre}</div>
						<div style="font-size: 0.8rem; color: var(--color-text-muted);">{u.email}</div>
						{#if u.puesto}
							<div style="font-size: 0.75rem; color: var(--color-text-muted);">💼 {u.puesto}</div>
						{/if}
					</div>
					<div style="display:flex;align-items:center;gap:0.5rem;">
						{#if u.mac_telefono}
							<span class="badge badge-mac" title="MAC del teléfono (Detección de Red 📡)">📡 {u.mac_telefono}</span>
						{/if}
						{#if u.acceso_usuarios}
							<span class="badge badge-warning">admin</span>
						{:else}
							<span class="badge badge-info">usuario</span>
						{/if}
						<span style="color: var(--color-text-muted);">›</span>
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	/* MAC del teléfono (Detección de Red 📡): monoespaciada para leerla de un
	   vistazo. Va aquí y no en styles/app.css porque ese archivo es del shell
	   canónico (lo genera tools/sync_shell.py) y el CI lo valida. */
	.badge-mac {
		background: rgba(52, 211, 153, 0.14);
		color: #34D399;
		font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
		letter-spacing: 0.02em;
	}
	/* 📷 Avatar: la foto del usuario, o sus iniciales si no tiene (o no se pudo
	   cargar). Estilo local, no en styles/app.css (shell canónico). */
	.avatar {
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 999px;
		flex-shrink: 0;
		overflow: hidden;
		background: rgba(255, 255, 255, 0.08);
		border: 1px solid rgba(255, 255, 255, 0.15);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.avatar.mini { opacity: 0.5; }
	.avatar img { width: 100%; height: 100%; object-fit: cover; }
	.avatar span { font-size: 0.85rem; font-weight: 700; color: var(--color-text-muted); }
</style>
