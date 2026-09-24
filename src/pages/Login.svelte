<script>
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);
	let privateMode = $state(false);

	// Detectar navegación privada: localStorage no persiste ahí
	try {
		localStorage.setItem('__t', '1');
		if (localStorage.getItem('__t') !== '1') privateMode = true;
		localStorage.removeItem('__t');
	} catch {
		privateMode = true;
	}

	async function login() {
		if (!email || !password) {
			error = 'Por favor, complete todos los campos.';
			return;
		}
		loading = true;
		error = '';
		try {
			await auth.login(email, password);
			navigate('/dashboard', { replace: true });
		} catch (e) {
			error = e.message || 'Usuario o contraseña incorrectos.';
		} finally {
			loading = false;
		}
	}

	function limpiar() {
		email = '';
		password = '';
		error = '';
	}
</script>

<div class="login-page">
	<div class="login-card">
		<img class="logo-img" src="/admon_logo.png" alt="Admon ECCSA" />
		<h1>ADMON</h1>
		<p class="subtitle">ECCSA AUTOMATION</p>

		{#if privateMode}
			<div class="error">⚠️ Estás en navegación privada: la sesión NO se guardará al cerrar el navegador. Abre en una pestaña normal para mantener la sesión.</div>
		{/if}

		<form on:submit={(e) => { e.preventDefault(); login(); }}>
			<div class="field">
				<label for="email">Usuario o Correo:</label>
				<input
					id="email"
					type="email"
					class="input"
					placeholder="usuario@ecc-ssa.com.mx o usuario@ecc-sa.com.mx"
					autocomplete="username"
					bind:value={email}
				/>
			</div>

			<div class="field">
				<label for="password">Contraseña:</label>
				<input
					id="password"
					type="password"
					class="input"
					placeholder="Ingrese su contraseña"
					autocomplete="current-password"
					bind:value={password}
				/>
			</div>

			{#if error}
				<div class="error" style="margin-top:1rem;">
					{error}
				</div>
			{/if}

			<div class="field" style="margin-top:1rem;">
				<button type="submit" class="btn btn-primary btn-block" disabled={loading}>
					{loading ? 'Verificando…' : '🔑 Ingresar'}
				</button>
			</div>
			<button type="button" class="btn btn-secondary btn-block" style="margin-top:0.5rem" on:click={limpiar}>
				⬅️ Limpiar
			</button>
		</form>
	</div>
</div>

<style>
	.login-page {
		min-height: 100dvh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1.5rem;
		background: transparent;
	}
	.login-card {
		width: 100%;
		max-width: 360px;
		text-align: center;
	}
	.logo-img {
		width: 120px;
		height: 120px;
		object-fit: cover;
		border-radius: 24px;
		margin-bottom: 0.5rem;
	}
	h1 {
		font-size: 1.5rem;
		font-weight: 700;
		margin: 0 0 0.15rem;
		letter-spacing: 1px;
	}
	.subtitle {
		color: var(--color-text-muted);
		margin: 0 0 2rem;
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 2px;
	}
	.field {
		text-align: left;
		margin-bottom: 1rem;
	}
	.error {
		background: rgba(239, 68, 68, 0.1);
		color: #EF4444;
		padding: 0.75rem;
		border-radius: 8px;
		font-size: 0.85rem;
		margin-bottom: 1rem;
		text-align: left;
	}
</style>
