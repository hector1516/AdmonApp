<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';

	onMount(() => {
		if (!auth.isLoggedIn()) navigate('/login', { replace: true });
	});
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/dashboard')} title="Volver">⬅️</button>
		<h1>⚙️ Configuración</h1>
	</div>

	<div class="grid-2" style="margin-bottom: 0.75rem;">
		<div class="card">
			<h3 style="margin: 0 0 0.5rem; font-size: 0.9rem;">Base de Datos</h3>
			<p style="color: var(--color-text-muted); font-size: 0.85rem; margin: 0.15rem 0;">SQL Server · ECCSA_Admon</p>
			<p style="color: var(--color-text-muted); font-size: 0.85rem; margin: 0.15rem 0;">Usuario: sa</p>
		</div>
		<div class="card">
			<h3 style="margin: 0 0 0.5rem; font-size: 0.9rem;">Correo SMTP</h3>
			<p style="color: var(--color-text-muted); font-size: 0.85rem; margin: 0.15rem 0;">smtpout.secureserver.net:465</p>
			<p style="color: var(--color-text-muted); font-size: 0.85rem; margin: 0.15rem 0;">robot@ecc-sa.com.mx</p>
		</div>
	</div>

	<div class="card">
		<h3 style="margin: 0 0 0.5rem; font-size: 0.9rem;">App</h3>
		<p style="color: var(--color-text-muted); font-size: 0.85rem; margin: 0.15rem 0;">Versión: 1.0.0</p>
		<p style="color: var(--color-text-muted); font-size: 0.85rem; margin: 0.15rem 0;">Stack: Svelte 5 + FastAPI + PWA</p>
		<p style="color: var(--color-text-muted); font-size: 0.85rem; margin: 0.15rem 0;">Auth: JWT simple (sin passkeys)</p>
	</div>
</div>
