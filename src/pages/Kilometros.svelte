<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { api } from '$lib/api.js';
	import OfflineNotice from '../components/OfflineNotice.svelte';

	// Módulo Kilómetros — dos pestañas:
	//  1) Consumo: por automóvil, km de la semana (último registro − primero) y
	//     vales consumidos (tickets de Field) con su monto (todos son $500).
	//  2) Captura: odómetro por automóvil con fecha y hora (1 registro por día).
	// Los datos salen de HUB_RegistroKilometros, la MISMA tabla que escribe el
	// HUB y Field: lo que se captura en cualquiera de las apps se ve aquí.

	let tab = $state('consumo');
	let loading = $state(true);
	let error = $state('');
	let msg = $state('');

	// ── Consumo ───────────────────────────────────────────────────────────────
	let consumo = $state(null);
	let semanaOffset = $state(0); // 0 = semana en curso, -1 = anterior, ...
	let vehiculos = $state([]);
	let recientes = $state([]);

	// ── Captura ───────────────────────────────────────────────────────────────
	let selVehiculo = $state('');
	let km = $state(null);
	let fechaHora = $state('');
	let busy = $state(false);

	function tieneAcceso() {
		try {
			const u = JSON.parse(localStorage.getItem('admon_user') || 'null');
			return !!(u && u.acceso_registro_kilometros);
		} catch {
			return false;
		}
	}

	function fmtNum(v) {
		return Number(v || 0).toLocaleString('es-MX');
	}

	function fmtMXN(v) {
		return '$' + Number(v || 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}

	// 'YYYY-MM-DDTHH:MM' en hora local del dispositivo (lo natural para "ahora").
	function ahoraLocalInput() {
		const d = new Date();
		const p = (x) => String(x).padStart(2, '0');
		return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
	}

	function fmtFecha(iso) {
		if (!iso) return '—';
		const d = new Date(iso);
		if (isNaN(d.getTime())) return '—';
		const p = (x) => String(x).padStart(2, '0');
		return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
	}

	let vehiculoSel = $derived(vehiculos.find((v) => String(v.id) === String(selVehiculo)) || null);

	async function cargarConsumo() {
		const d = consumo;
		let url = '/kilometros/consumo';
		if (d && d.semana) url += `?anio=${d.semana.anio}&semana=${d.semana.num}`;
		consumo = await api.get(url);
	}

	async function cargarTodo() {
		loading = true;
		error = '';
		try {
			// api.get: red -> IndexedDB -> copia local (el consumo también abre sin red).
			consumo = await api.get('/kilometros/consumo');
			vehiculos = (await api.get('/kilometros/vehiculos')) || [];
			recientes = (await api.get('/kilometros/recientes?n=15')) || [];
			if (!selVehiculo && vehiculos.length) {
				selVehiculo = String(vehiculos[0].id);
				km = vehiculos[0].km_actuales;
			}
		} catch (e) {
			error = e.message === 'Sesión expirada' ? e.message : e.message || 'No se pudo cargar.';
		} finally {
			loading = false;
		}
	}

	// Semana ISO de una fecha (algoritmo estándar: jueves de la semana define el año).
	function isoWeekOf(date) {
		const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
		const dia = d.getUTCDay() || 7;
		d.setUTCDate(d.getUTCDate() + 4 - dia);
		const inicioAnio = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
		return { anio: d.getUTCFullYear(), semana: Math.ceil(((d - inicioAnio) / 86400000 + 1) / 7) };
	}

	// Cambiar de semana: se pide la anterior a la que ya está cargada.
	async function moverSemana(delta) {
		busy = true;
		error = '';
		try {
			const s = consumo?.semana;
			if (!s) return;
			const d = new Date(s.inicio + 'T00:00:00');
			d.setDate(d.getDate() + delta * 7);
			const { anio, semana } = isoWeekOf(d);
			consumo = await api.get(`/kilometros/consumo?anio=${anio}&semana=${semana}`);
		} catch (e) {
			error = e.message || 'No se pudo cambiar de semana.';
		} finally {
			busy = false;
		}
	}

	function volverACurrent() {
		consumo = null;
		api.get('/kilometros/consumo').then((c) => (consumo = c)).catch((e) => (error = e.message));
	}

	function alElegirVehiculo() {
		// El odómetro nunca puede bajar: el mínimo es la última lectura.
		km = vehiculoSel ? vehiculoSel.km_actuales : null;
	}

	async function registrar() {
		error = '';
		msg = '';
		if (!selVehiculo) {
			error = 'Elige un automóvil.';
			return;
		}
		if (km === null || km === undefined || km === '' || isNaN(Number(km))) {
			error = 'Escribe los kilómetros del odómetro.';
			return;
		}
		busy = true;
		try {
			const r = await api.post('/kilometros/registro', {
				id_automovil: Number(selVehiculo),
				kilometros: Number(km),
				fecha_hora: fechaHora || ahoraLocalInput()
			});
			msg = `✅ Kilometraje registrado: ${fmtNum(r.kilometros)} km — ${r.vehiculo}`;
			// Recargar todo para reflejar el consumo de la semana de inmediato.
			consumo = null;
			await cargarTodo();
		} catch (e) {
			error = e.message || 'No se pudo registrar.';
		} finally {
			busy = false;
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
		fechaHora = ahoraLocalInput();
		await cargarTodo();
	});
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" onclick={() => navigate('/dashboard')} title="Volver">⬅️</button>
		<h1>🛣️ Kilómetros</h1>
	</div>

	<OfflineNotice />

	<div class="tabs">
		<button class="tab" class:active={tab === 'consumo'} onclick={() => (tab = 'consumo')}>📊 Consumo semanal</button>
		<button class="tab" class:active={tab === 'captura'} onclick={() => (tab = 'captura')}>✍️ Capturar kilómetros</button>
	</div>

	{#if error}<div class="msg err">⚠️ {error}</div>{/if}
	{#if msg}<div class="msg ok">{msg}</div>{/if}

	{#if loading}
		<div class="state">⏳ Cargando…</div>
	{:else if tab === 'consumo'}
		<!-- ═══ CONSUMO ═══ -->
		{#if !consumo}
			<div class="state">Sin datos de consumo.</div>
		{:else}
			{@const r = consumo.resumen}
			<div class="semana-bar">
				<button class="btn btn-sm btn-secondary" onclick={() => moverSemana(-1)} disabled={busy} title="Semana anterior">◀</button>
				<div class="semana-txt">
					<div class="semana-lbl">Semana {consumo.semana.num} del {consumo.semana.anio}</div>
					<div class="semana-rango">{consumo.semana.etiqueta}</div>
				</div>
				<button class="btn btn-sm btn-secondary" onclick={() => moverSemana(1)} disabled={busy} title="Semana siguiente">▶</button>
				<button class="btn btn-sm btn-ghost" onclick={volverACurrent} disabled={busy}>Esta semana</button>
			</div>

			<div class="cards">
				<div class="card-kpi">
					<div class="kpi-lbl">Consumo de la flota</div>
					<div class="kpi-val">{fmtNum(r.consumo_km)} <span class="kpi-unit">km</span></div>
					<div class="kpi-sub" class:sube={r.consumo_km > r.consumo_ant} class:baja={r.consumo_km < r.consumo_ant}>
						{#if r.consumo_ant > 0}
							{r.consumo_km >= r.consumo_ant ? '▲' : '▼'} {fmtNum(Math.abs(r.consumo_km - r.consumo_ant))} km vs. semana anterior
						{:else}
							sin referencia de la semana anterior
						{/if}
					</div>
				</div>
				<div class="card-kpi">
					<div class="kpi-lbl">Vales consumidos</div>
					<div class="kpi-val">{fmtNum(r.vales)}</div>
					<div class="kpi-sub">{fmtMXN(r.monto_vales)} · {fmtMXN(consumo.monto_vale)} c/u</div>
				</div>
				<div class="card-kpi">
					<div class="kpi-lbl">Automóviles con lectura</div>
					<div class="kpi-val">{r.con_registro}<span class="kpi-unit">/{r.vehiculos}</span></div>
					<div class="kpi-sub">{r.requieren_servicio > 0 ? `⚠️ ${r.requieren_servicio} requieren servicio (≥9,500 km)` : '✅ Ninguno requiere servicio'}</div>
				</div>
			</div>

			<p class="hint">
				Consumo = último registro de la semana − primero. Con una sola lectura no hay diferencia
				posible, por eso se marca “1 lectura”. Vales = tickets de gasolina capturados en Field
				(x {fmtMXN(consumo.monto_vale)} cada uno).
			</p>

			<div class="table-wrap">
				<table>
					<thead>
						<tr>
							<th>Placas</th><th>Automóvil</th><th>Conductor</th>
							<th class="num">Lecturas</th><th class="num">Primero</th><th class="num">Último</th>
							<th class="num">Consumo</th><th class="num">Vales</th><th class="num">Monto</th>
						</tr>
					</thead>
					<tbody>
						{#each consumo.vehiculos as v (v.id)}
							{@const delta = v.consumo_km - v.consumo_ant}
							<tr class:sin-lectura={v.registros === 0}>
								<td class="mono">{v.placas || '—'}</td>
								<td>{v.marca_modelo || '—'}</td>
								<td class="muted">{v.conductor || '—'}</td>
								<td class="num">
									{#if v.registros === 0}<span class="pill warn">sin lectura</span>
									{:else if v.registros === 1}<span class="pill">1 lectura</span>
									{:else}{v.registros}{/if}
								</td>
								<td class="num mono">{v.primer_km === null ? '—' : fmtNum(v.primer_km)}</td>
								<td class="num mono">{v.ultimo_km === null ? '—' : fmtNum(v.ultimo_km)}</td>
								<td class="num">
									{#if v.registros >= 2}
										<strong>{fmtNum(v.consumo_km)}</strong>
										{#if v.consumo_ant > 0}
											<span class="delta" class:subio={delta > 0} class:bajo={delta < 0}>
												{delta > 0 ? '▲' : delta < 0 ? '▼' : '='}{Math.abs(delta) ? fmtNum(Math.abs(delta)) : ''}
											</span>
										{/if}
									{:else}—{/if}
								</td>
								<td class="num">{v.vales ? v.vales : '—'}</td>
								<td class="num">{v.vales ? fmtMXN(v.monto_vales) : '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}

		{#if recientes.length}
			<h2 class="sub">🕐 Últimas capturas</h2>
			<div class="table-wrap">
				<table>
					<thead><tr><th>Fecha y hora</th><th>Automóvil</th><th>Conductor</th><th class="num">Kilómetros</th></tr></thead>
					<tbody>
						{#each recientes as k (k.id)}
							<tr>
								<td class="mono">{fmtFecha(k.fecha_hora)}</td>
								<td>{k.marca_modelo} <span class="muted mono">{k.placas}</span></td>
								<td class="muted">{k.usuario || '—'}</td>
								<td class="num mono">{fmtNum(k.kilometros)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{:else}
		<!-- ═══ CAPTURA ═══ -->
		<div class="card">
			<div class="card-title">✍️ Registrar odómetro</div>
			<div class="field">
				<label for="km-veh">Automóvil:</label>
				<select id="km-veh" class="input" bind:value={selVehiculo} onchange={alElegirVehiculo}>
					{#each vehiculos as v (v.id)}
						<option value={String(v.id)}>
							{v.marca_modelo} · {v.placas} — {fmtNum(v.km_actuales)} km{v.conductor ? ` (${v.conductor})` : ''}
						</option>
					{/each}
				</select>
				{#if vehiculoSel}
					<p class="hint" style="margin: 0.35rem 0 0;">
						Última lectura: <strong>{fmtNum(vehiculoSel.km_actuales)} km</strong>
						{vehiculoSel.ultima_lectura ? `(${fmtFecha(vehiculoSel.ultima_lectura)})` : '(sin registros)'} ·
						mínimo {fmtNum(vehiculoSel.km_actuales)} km
						{#if vehiculoSel.requiere_servicio}<span class="pill warn" style="margin-left: 0.4rem;">requiere servicio</span>{/if}
					</p>
				{/if}
			</div>
			<div class="grid-2">
				<div class="field">
					<label for="km-valor">Kilómetros del odómetro:</label>
					<input id="km-valor" class="input" type="number" min={vehiculoSel ? vehiculoSel.km_actuales : 0} step="1"
						bind:value={km} placeholder="Odómetro actual" />
				</div>
				<div class="field">
					<label for="km-fecha">Fecha y hora:</label>
					<input id="km-fecha" class="input" type="datetime-local" bind:value={fechaHora} />
				</div>
			</div>
			<button class="btn btn-primary btn-block" onclick={registrar} disabled={busy || !selVehiculo}>
				{busy ? 'Guardando…' : '💾 Registrar kilómetros'}
			</button>
			<p class="hint" style="margin: 0.6rem 0 0;">
				Un registro por automóvil por día. Lo capturado aquí o en el HUB aparece en la pestaña de consumo.
			</p>
		</div>
	{/if}
</div>

<style>
	.page { max-width: 1200px; margin: 0 auto; padding: 1rem; }
	.header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
	.header h1 { font-size: 1.25rem; margin: 0; color: #f1f5f9; }

	.tabs { display: flex; gap: 0.25rem; border-bottom: 1px solid var(--color-border); margin-bottom: 1rem; }
	.tab { background: transparent; border: 0; border-bottom: 2px solid transparent; color: var(--color-text-muted);
		padding: 0.6rem 0.9rem; font: inherit; cursor: pointer; font-weight: 600; }
	.tab.active { color: #FFAE00; border-bottom-color: #FF6B00; }
	.tab:hover { color: #f1f5f9; }

	.msg { padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 0.75rem; }
	.msg.err { background: rgba(239, 68, 68, 0.1); color: #f87171; }
	.msg.ok { background: rgba(34, 197, 94, 0.1); color: #4ade80; }
	.state { text-align: center; color: #94a3b8; padding: 3rem 1rem; font-size: 0.9rem; }
	.hint { font-size: 0.75rem; color: #64748b; margin: 0 0 0.9rem; }
	.muted { color: var(--color-text-muted); }
	.mono { font-family: ui-monospace, 'Cascadia Mono', monospace; }
	.sub { font-size: 0.95rem; color: #f1f5f9; margin: 1.2rem 0 0.5rem; }

	/* Barra de semana */
	.semana-bar { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.9rem; }
	.semana-txt { text-align: center; min-width: 190px; }
	.semana-lbl { font-weight: 700; color: #f1f5f9; font-size: 0.9rem; }
	.semana-rango { font-size: 0.75rem; color: var(--color-text-muted); }
	.btn-ghost { background: transparent; border: 1px solid var(--color-border); color: var(--color-text-muted); }
	.btn-ghost:hover { color: #f1f5f9; }

	/* KPIs */
	.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
	.card-kpi { background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 14px; padding: 0.85rem 1rem; }
	.kpi-lbl { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; color: #94a3b8; font-weight: 700; }
	.kpi-val { font-size: 1.7rem; font-weight: 800; color: #f1f5f9; line-height: 1.2; }
	.kpi-unit { font-size: 0.9rem; color: #94a3b8; font-weight: 600; }
	.kpi-sub { font-size: 0.72rem; color: var(--color-text-muted); }
	.kpi-sub.sube { color: #fbbf24; }
	.kpi-sub.baja { color: #4ade80; }

	/* Tabla */
	.table-wrap { overflow-x: auto; border: 1px solid var(--color-border); border-radius: 12px; }
	table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
	th, td { padding: 0.5rem 0.6rem; text-align: left; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
	th { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; background: rgba(255, 255, 255, 0.03); }
	td.num, th.num { text-align: right; }
	tbody tr:hover { background: rgba(255, 255, 255, 0.03); }
	tr.sin-lectura td { opacity: 0.55; }
	.pill { display: inline-block; font-size: 0.65rem; font-weight: 700; padding: 0.1rem 0.45rem; border-radius: 999px;
		background: rgba(148, 163, 184, 0.15); color: #cbd5e1; }
	.pill.warn { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
	.delta { font-size: 0.68rem; margin-left: 0.35rem; color: #94a3b8; }
	.delta.subio { color: #fbbf24; }
	.delta.bajo { color: #4ade80; }

	.card { background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 14px; padding: 1rem; }
	.card-title { font-weight: 700; color: #f1f5f9; margin-bottom: 0.75rem; }
	.field { margin-bottom: 0.75rem; }
	.field label { display: block; font-size: 0.78rem; color: #cbd5e1; margin-bottom: 0.3rem; }
	.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
	@media (max-width: 640px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
