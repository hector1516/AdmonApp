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
		<h1>📱 Telegram - Alertas</h1>
	</div>

	<div class="card" style="margin-bottom: 0.75rem;">
		<h3 style="margin: 0 0 0.5rem; font-size: 0.95rem;">Configuración del Bot</h3>
		<p style="color: var(--color-text-muted); font-size: 0.9rem; margin: 0 0 0.75rem;">
			El bot de Telegram está configurado y enviará alertas automáticas.
		</p>
		<div class="grid-2">
			<div>
				<span style="color: var(--color-text-muted); font-size: 0.85rem;">Token: </span>
				<span class="badge badge-success">configurado</span>
			</div>
			<div>
				<span style="color: var(--color-text-muted); font-size: 0.85rem;">Chat ID: </span>
				<span class="badge badge-success">configurado</span>
			</div>
		</div>
	</div>

	<div class="card">
		<h3 style="margin: 0 0 0.75rem; font-size: 0.95rem;">Alertas activas</h3>
		<div class="list">
			<div class="list-card" style="cursor: default;"><span>📈 Tipo de cambio USD/MXN</span><span class="badge badge-info">6:00 AM</span></div>
			<div class="list-card" style="cursor: default;"><span>🎁 Vales OxxoGas</span><span class="badge badge-info">cada hora</span></div>
			<div class="list-card" style="cursor: default;"><span>🖼️ Wallpapers Bing</span><span class="badge badge-info">cada 6 h</span></div>
		</div>
	</div>

	<p style="text-align: center; font-size: 0.8rem; color: var(--color-text-muted); margin-top: 1rem;">
		Workers corriendo en segundo plano.
	</p>
</div>
