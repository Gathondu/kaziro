<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { loginSchema } from '$lib/schemas/auth';
	import { getUser, isAuthReady } from '$lib/stores/auth';
	import { supabase } from '$lib/supabase';
	import Button from '$lib/components/ui/Button.svelte';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';

	let email = $state('');
	let password = $state('');
	let fieldErrors = $state<Record<string, string>>({});
	let formError = $state<string | null>(null);
	let pending = $state(false);

	$effect(() => {
		if (!browser || !isAuthReady()) return;
		if (getUser()) {
			const next = $page.url.searchParams.get('next') || '/dashboard';
			void goto(next);
		}
	});

	async function submit(e: Event): Promise<void> {
		e.preventDefault();
		formError = null;
		fieldErrors = {};
		const parsed = loginSchema.safeParse({ email, password });
		if (!parsed.success) {
			for (const iss of parsed.error.issues) {
				const k = String(iss.path[0] ?? 'form');
				fieldErrors = { ...fieldErrors, [k]: iss.message };
			}
			return;
		}
		pending = true;
		const { error } = await supabase.auth.signInWithPassword({
			email: parsed.data.email,
			password: parsed.data.password
		});
		pending = false;
		if (error) {
			formError = error.message;
			return;
		}
		const next = $page.url.searchParams.get('next') || '/dashboard';
		await goto(next);
	}

	function onEmailInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'email');
	}

	function onPasswordInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'password');
	}
</script>

<svelte:head>
	<title>Log in — Kaziro</title>
</svelte:head>

<h1 class="mb-4 text-xl font-semibold">Log in</h1>
<form class="space-y-4" onsubmit={submit}>
	<label class="form-control">
		<span class="label-text font-medium">Email</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.email
				? 'input-error'
				: ''}"
			type="email"
			autocomplete="email"
			bind:value={email}
			oninput={onEmailInput}
		/>
		{#if fieldErrors.email}<span class="label-text-alt text-error">{fieldErrors.email}</span>{/if}
	</label>
	<label class="form-control">
		<span class="label-text font-medium">Password</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.password
				? 'input-error'
				: ''}"
			type="password"
			autocomplete="current-password"
			bind:value={password}
			oninput={onPasswordInput}
		/>
		{#if fieldErrors.password}<span class="label-text-alt text-error">{fieldErrors.password}</span
			>{/if}
	</label>
	{#if formError}
		<p class="text-sm text-error" role="alert">{formError}</p>
	{/if}
	<Button type="submit" disabled={pending}>{pending ? 'Signing in…' : 'Sign in'}</Button>
</form>
<p class="mt-4 text-sm text-base-content/70">
	<a class="link link-primary font-medium" href="/forgot-password">Forgot password?</a>
	·
	<a class="link font-medium" href="/signup">Create an account</a>
</p>
