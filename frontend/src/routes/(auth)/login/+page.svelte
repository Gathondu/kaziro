<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { loginSchema } from '$lib/schemas/auth';
	import { ApiError } from '$lib/api/errors';
	import { assertAppAccountWithAccessToken } from '$lib/api/me';
	import { getUser, isAuthReady } from '$lib/stores/auth';
	import { supabase } from '$lib/supabase';
	import Button from '$lib/components/ui/Button.svelte';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';

	let email = $state('');
	let password = $state('');
	let fieldErrors = $state<Record<string, string>>({});
	let formError = $state<string | null>(null);
	let pending = $state(false);
	/** Blocks auto-redirect while we verify app account (Supabase can be valid when Kaziro user is off). */
	let verifyingAppAccount = $state(false);
	let showedDeactivatedFromQuery = $state(false);

	$effect(() => {
		if (!browser || !isAuthReady() || verifyingAppAccount) return;
		if (!showedDeactivatedFromQuery && $page.url.searchParams.get('deactivated') === '1') {
			showedDeactivatedFromQuery = true;
			formError =
				'This account has been deactivated. Contact support if you believe this is a mistake.';
		}
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
		verifyingAppAccount = true;
		const { data, error } = await supabase.auth.signInWithPassword({
			email: parsed.data.email,
			password: parsed.data.password
		});
		if (error) {
			verifyingAppAccount = false;
			pending = false;
			formError = error.message;
			return;
		}
		const accessToken = data.session?.access_token;
		if (!accessToken) {
			verifyingAppAccount = false;
			pending = false;
			formError = 'No session returned. Try again.';
			return;
		}
		try {
			await assertAppAccountWithAccessToken(accessToken);
		} catch (e) {
			verifyingAppAccount = false;
			pending = false;
			formError =
				e instanceof ApiError && e.code === 'user_deactivated'
					? e.message
					: e instanceof ApiError
						? e.message
						: 'Could not verify your account. Try again.';
			return;
		}
		verifyingAppAccount = false;
		pending = false;
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
	<label class="block space-y-1.5">
		<span class="text-sm font-medium">Email</span>
		<input
			class="bg-base-200 text-base-content placeholder:text-base-content/45 block w-full rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none {fieldErrors.email
				? 'border-error focus:ring-error/35'
				: 'border-base-300 focus:border-primary focus:ring-primary/25'}"
			type="email"
			autocomplete="email"
			bind:value={email}
			oninput={onEmailInput}
		/>
		{#if fieldErrors.email}<span class="text-error text-xs">{fieldErrors.email}</span>{/if}
	</label>
	<label class="block space-y-1.5">
		<span class="text-sm font-medium">Password</span>
		<input
			class="bg-base-200 text-base-content placeholder:text-base-content/45 block w-full rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none {fieldErrors.password
				? 'border-error focus:ring-error/35'
				: 'border-base-300 focus:border-primary focus:ring-primary/25'}"
			type="password"
			autocomplete="current-password"
			bind:value={password}
			oninput={onPasswordInput}
		/>
		{#if fieldErrors.password}<span class="text-error text-xs">{fieldErrors.password}</span>{/if}
	</label>
	{#if formError}
		<p class="text-error text-sm" role="alert">{formError}</p>
	{/if}
	<Button type="submit" class="h-11 w-full justify-center" disabled={pending}
		>{pending ? 'Signing in…' : 'Sign in'}</Button
	>
</form>
<p class="text-base-content/70 mt-4 text-sm">
	<a class="text-primary font-medium underline-offset-4 hover:underline" href="/forgot-password"
		>Forgot password?</a
	>
	·
	<a class="font-medium underline-offset-4 hover:underline" href="/signup">Create an account</a>
</p>
