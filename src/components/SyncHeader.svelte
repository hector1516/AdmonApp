<script>
	// Banner superior clonado de Field: estado de sincronía + usuario logueado.
	// Diferencias vs Field: SIN vehículo asignado (Admon no opera vehículos).
	import { online, onlinePing } from '$lib/stores/online.js';
	import { auth } from '$lib/stores/auth.js';

	let syncing = false;
	// Fase 1: sin cola offline -> 0 pendientes = "Todo sincronizado"
	let pendingCount = 0;

	async function forceSync() {
		if (!$online || syncing) return;
		syncing = true;
		try {
			await onlinePing();
		} catch {}
		syncing = false;
	}
</script>

<button
	class="sync-header"
	class:offline={!$online}
	class:syncing
	class:has-items={pendingCount > 0}
	on:click={forceSync}
>
	{#if !$online}
		<span class="dot offline"></span><span>Sin conexión — modo offline</span>
	{:else if syncing}
		<span class="dot syncing"></span><span>Sincronizando...</span>
	{:else if pendingCount > 0}
		<span class="dot pending"></span><span>{pendingCount} pendiente{pendingCount > 1 ? 's' : ''} — toca para sincronizar</span>
	{:else}
		<span class="dot ok"></span><span>Todo sincronizado</span>
	{/if}
	{#if $auth.user}
		<span class="who">👤 {$auth.user.nombre}</span>
	{/if}
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
