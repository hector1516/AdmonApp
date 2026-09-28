<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { api } from '$lib/api.js';

	// Notas del equipo (HUB_Notas · migración 0040). Tablero interno: todas
	// las personas logueadas ven las notas y cualquiera puede crear, editar y
	// borrar; cada nota muestra su autor. Sin permiso propio (igual que ECCSA IA).
	// El panel resumen vive en el Dashboard (/dashboard).

	let notas = $state([]);
	let loading = $state(true);
	let error = $state('');
	let aviso = $state('');

	// Editor en panel (sin popup): abierto = 'nueva' | id de la nota | null
	let editorAbierto = $state(false);
	let editandoId = $state(null);
	let formTitulo = $state('');
	let formContenido = $state('');
	let guardando = $state(false);

	// La BD guarda hora de México sin offset: se renderiza tal cual (componentes
	// del string) para que se vea igual en cualquier dispositivo.
	function fmtFecha(iso) {
		if (!iso) return '—';
		const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
		if (m) return `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}`;
		return '—';
	}

	async function cargar() {
		try {
			notas = (await api.get('/notas')) || [];
			error = '';
		} catch (e) {
			error = e.message === 'Sesión expirada' ? e.message : 'No se pudieron cargar las notas.';
		} finally {
			loading = false;
		}
	}

	function abrirNueva() {
		editandoId = null;
		formTitulo = '';
		formContenido = '';
		editorAbierto = true;
		aviso = '';
	}

	function abrirEditar(n) {
		editandoId = n.id;
		formTitulo = n.titulo;
		formContenido = n.contenido;
		editorAbierto = true;
		aviso = '';
	}

	function cancelarEditor() {
		editorAbierto = false;
		editandoId = null;
	}

	async function guardar() {
		if (!formTitulo.trim() || !formContenido.trim()) {
			error = 'El título y el contenido no pueden estar vacíos.';
			return;
		}
		guardando = true;
		error = '';
		try {
			if (editandoId === null) {
				const creada = await api.post('/notas', { titulo: formTitulo, contenido: formContenido });
				notas = [creada, ...notas];
				aviso = '✅ Nota creada.';
			} else {
				const editada = await api.put(`/notas/${editandoId}`, { titulo: formTitulo, contenido: formContenido });
				notas = notas.map((n) => (n.id === editandoId ? editada : n));
				aviso = '✅ Nota actualizada.';
			}
			cancelarEditor();
		} catch (e) {
			error = e.message || 'No se pudo guardar la nota.';
		} finally {
			guardando = false;
		}
	}

	async function borrar(n) {
		if (!confirm(`¿Borrar la nota "${n.titulo}"?`)) return;
		error = '';
		try {
			await api.delete(`/notas/${n.id}`);
			notas = notas.filter((x) => x.id !== n.id);
			if (editandoId === n.id) cancelarEditor();
			aviso = '🗑️ Nota borrada.';
		} catch (e) {
			error = e.message || 'No se pudo borrar la nota.';
		}
	}

	onMount(async () => {
		if (!auth.isLoggedIn()) {
			navigate('/login', { replace: true });
			return;
		}
		await cargar();
	});
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" onclick={() => navigate('/dashboard')} title="Volver">⬅️</button>
		<h1>📝 Notas</h1>
		<div style="flex:1"></div>
		<button class="btn btn-sm btn-primary" onclick={abrirNueva}>➕ Nueva nota</button>
	</div>

	{#if aviso}
		<div class="nota-aviso">{aviso}</div>
	{/if}
	{#if error}
		<div class="state err">⚠️ {error}</div>
	{/if}

	<!-- Editor en panel (sin popup): se abre arriba de la lista -->
	{#if editorAbierto}
		<div class="editor">
			<div class="editor-title">{editandoId === null ? '➕ Nueva nota' : '✏️ Editar nota'}</div>
			<div class="field">
				<input class="input" placeholder="Título de la nota" bind:value={formTitulo} maxlength="200" />
			</div>
			<div class="field">
				<textarea class="input editor-contenido" rows="6" placeholder="Escribe el contenido…" bind:value={formContenido}></textarea>
			</div>
			<div class="editor-acciones">
				<button class="btn btn-sm btn-primary" onclick={guardar} disabled={guardando || !formTitulo.trim() || !formContenido.trim()}>
					{guardando ? '⏳ Guardando…' : '💾 Guardar'}
				</button>
				<button class="btn btn-sm btn-secondary" onclick={cancelarEditor} disabled={guardando}>Cancelar</button>
			</div>
		</div>
	{/if}

	<p class="hint">Notas compartidas del equipo · cada nota muestra quién la escribió · cualquiera puede editarlas o borrarlas</p>

	{#if loading}
		<div class="state">⏳ Cargando notas…</div>
	{:else if notas.length === 0}
		<div class="state">📝 No hay notas todavía. ¡Crea la primera con “➕ Nueva nota”!</div>
	{:else}
		<div class="notas-lista">
			{#each notas as n (n.id)}
				<article class="nota-card">
					<div class="nota-head">
						<h2 class="nota-titulo">{n.titulo}</h2>
						<div class="nota-acciones">
							<button class="btn-icon" onclick={() => abrirEditar(n)} title="Editar">✏️</button>
							<button class="btn-icon" onclick={() => borrar(n)} title="Borrar">🗑️</button>
						</div>
					</div>
					<div class="nota-contenido">{n.contenido}</div>
					<div class="nota-meta">
						<span class="nota-autor">👤 {n.autor}</span>
						<span>🕒 {fmtFecha(n.fecha_creacion)}{n.fecha_actualizado ? ` · editada ${fmtFecha(n.fecha_actualizado)}` : ''}</span>
					</div>
				</article>
			{/each}
		</div>
	{/if}
</div>

<style>
	.nota-aviso {
		padding: 0.5rem 0.75rem;
		background: rgba(34, 197, 94, 0.12);
		color: #22C55E;
		font-size: 0.8rem;
		border-radius: 8px;
		margin-bottom: 0.75rem;
	}

	/* Editor en panel */
	.editor {
		background: var(--color-surface);
		border: 1px solid var(--color-primary);
		border-radius: 14px;
		padding: 1rem;
		margin-bottom: 1rem;
	}
	.editor-title { font-weight: 700; font-size: 0.95rem; margin-bottom: 0.75rem; }
	.editor .field { margin-bottom: 0.6rem; }
	.editor-contenido { resize: vertical; min-height: 120px; line-height: 1.5; }
	.editor-acciones { display: flex; gap: 0.5rem; }

	/* Lista de notas */
	.notas-lista { display: flex; flex-direction: column; gap: 0.8rem; }
	.nota-card {
		background: var(--color-surface);
		border: 1px solid rgba(255, 255, 255, 0.06);
		border-radius: 14px;
		padding: 0.9rem 1rem;
	}
	.nota-head { display: flex; align-items: flex-start; gap: 0.5rem; }
	.nota-titulo { font-size: 1rem; margin: 0; flex: 1; line-height: 1.3; }
	.nota-acciones { display: flex; gap: 0.15rem; flex-shrink: 0; }
	.btn-icon {
		background: transparent;
		border: none;
		font-size: 0.95rem;
		cursor: pointer;
		padding: 0.25rem 0.4rem;
		border-radius: 8px;
		transition: background 0.1s;
	}
	.btn-icon:hover { background: rgba(255, 255, 255, 0.07); }
	.nota-contenido {
		white-space: pre-wrap;
		word-wrap: break-word;
		font-size: 0.88rem;
		line-height: 1.55;
		color: var(--color-text);
		margin-top: 0.45rem;
	}
	.nota-meta {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: 0.4rem;
		margin-top: 0.7rem;
		padding-top: 0.55rem;
		border-top: 1px solid rgba(255, 255, 255, 0.06);
		font-size: 0.72rem;
		color: var(--color-text-muted);
	}
	.nota-autor { font-weight: 600; color: var(--color-text); }
</style>
