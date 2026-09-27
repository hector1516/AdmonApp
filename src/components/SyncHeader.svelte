<script>
	// Banner superior clonado de Field: estado de sincronía + usuario logueado.
	// Diferencias vs Field: SIN vehículo asignado (Admon no opera vehículos).
	import { get } from 'svelte/store';
	import { online, onlinePing } from '$lib/stores/online.js';
	import { auth } from '$lib/stores/auth.js';
	import { pendingCount, syncing, syncPush, refreshPending } from '$lib/sync.js';
	import { APP_VERSION, SHELL_VERSION } from '$lib/shell.js';
	import { onMount } from 'svelte';

	// Banner común ECCSA-Shell: además del estado de sync y el usuario,
	// muestra la versión de la app/shell y si estás en la oficina o remoto.
	let lugar = 'desconocido';
	let ip = '';

	onMount(async () => {
		try {
			const r = await fetch('/api/shell/state', { credentials: 'same-origin' });
			if (!r.ok) return;
			const d = await r.json();
			lugar = d.lugar?.modo || 'desconocido';
			ip = d.lugar?.ip || '';
		} catch (e) { /* fail silent: el shell no tumba la app */ }
	});

	$: lugarTxt = lugar === 'oficina' ? 'Oficina' : lugar === 'remoto' ? 'Remoto' : '—';
	$: lugarIcono = lugar === 'oficina' ? '🏢' : lugar === 'remoto' ? '🏠' : '📍';

	async function forceSync() {
		if (!get(online) || get(syncing)) return;
		await onlinePing();
		await syncPush();
		refreshPending();
	}
</script>

<button
	class="sync-header"
	class:offline={!$online}
	class:syncing={$syncing}
	class:has-items={$pendingCount > 0}
	on:click={forceSync}
>
{#if !$online}
		<span class="dot offline"></span><span>Sin conexión — modo offline</span>
	{:else if $syncing}
		<span class="dot syncing"></span><span>Sincronizando...</span>
	{:else if $pendingCount > 0}
		<span class="dot pending"></span><span>{$pendingCount} pendiente{$pendingCount > 1 ? 's' : ''} — toca para sincronizar</span>
	{:else}
		<span class="dot ok"></span><span>Todo sincronizado</span>
	{/if}
	{#if $auth.user}
		<span class="who">👤 {$auth.user.nombre}</span>
	{/if}
	<span class="lugar {lugar}" title={ip}>{lugarIcono} {lugarTxt}</span>
	<span class="vers">v{APP_VERSION} · shell {SHELL_VERSION}</span>
</button>

<style>
	.sync-header {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 250;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.45rem;
		flex-wrap: wrap;
		width: 100%;
		padding: calc(0.55rem + env(safe-area-inset-top)) 1rem 0.55rem;
		background: rgba(30, 41, 59, 0.72);
		-webkit-backdrop-filter: blur(12px) saturate(1.2);
		backdrop-filter: blur(12px) saturate(1.2);
		color: var(--color-text);
		border: none;
		border-bottom: 1px solid rgba(255, 255, 255, 0.08);
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
		font-family: inherit;
	}
	.sync-header.offline { background: rgba(127, 29, 29, 0.78); }
	.sync-header.syncing { background: rgba(30, 58, 95, 0.78); }
	.sync-header.has-items { background: rgba(120, 53, 15, 0.78); }
	.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
	.dot.ok { background: #10B981; }
	.dot.pending { background: #F59E0B; animation: pulse 1.5s infinite; }
	.dot.syncing { background: #3B82F6; animation: spin 1s linear infinite; }
	.dot.offline { background: #EF4444; }
	.lugar, .vers {
		font-size: 0.7rem;
		font-weight: 500;
		color: var(--color-text-muted);
		white-space: nowrap;
	}
	.lugar.oficina { color: var(--color-success); }
	.lugar.remoto { color: var(--color-primary-light); }
	.vers { margin-left: auto; font-variant-numeric: tabular-nums; }
	@media (max-width: 820px) { .vers { display: none; } }
	@media (max-width: 430px) { .lugar { display: none; } }
	.who {
		flex-basis: 100%;
		text-align: center;
		font-size: 0.68rem;
		font-weight: 400;
		color: var(--color-text-muted);
	}

	@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
	@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
