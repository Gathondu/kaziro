<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { signupSchema } from '$lib/schemas/auth';
	import { getUser, isAuthReady } from '$lib/stores/auth';
	import { supabase } from '$lib/supabase';
	import Button from '$lib/components/ui/Button.svelte';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';
	import { saveOnboardingDraft } from '$lib/utils/onboarding';

	let email = $state('');
	let password = $state('');
	let confirm = $state('');
	let fieldErrors = $state<Record<string, string>>({});
	let formError = $state<string | null>(null);
	let pending = $state(false);

	$effect(() => {
		if (!browser || !isAuthReady()) return;
		if (getUser()) void goto('/dashboard');
	});

	async function submit(e: Event): Promise<void> {
		e.preventDefault();
		formError = null;
		fieldErrors = {};
		const parsed = signupSchema.safeParse({ email, password, confirm });
		if (!parsed.success) {
			for (const iss of parsed.error.issues) {
				const k = String(iss.path[0] ?? 'form');
				fieldErrors = { ...fieldErrors, [k]: iss.message };
			}
			return;
		}
		pending = true;
		const { error } = await supabase.auth.signUp({
			email: parsed.data.email,
			password: parsed.data.password
		});
		pending = false;
		if (error) {
			formError = error.message;
			return;
		}
		saveOnboardingDraft({ step: 1, profileSubStep: 'about', profile: {} });
		await goto('/onboarding/about-you');
	}

	function onEmailInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'email');
	}

	function onPasswordInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'password', 'confirm');
	}

	function onConfirmInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'confirm');
	}
</script>

<svelte:head>
	<title>Sign up — Kaziro</title>
</svelte:head>

<h1 class="mb-4 text-xl font-semibold">Create your account</h1>
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
			autocomplete="new-password"
			bind:value={password}
			oninput={onPasswordInput}
		/>
		{#if fieldErrors.password}<span class="text-error text-xs">{fieldErrors.password}</span>{/if}
	</label>
	<label class="block space-y-1.5">
		<span class="text-sm font-medium">Confirm password</span>
		<input
			class="bg-base-200 text-base-content placeholder:text-base-content/45 block w-full rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none {fieldErrors.confirm
				? 'border-error focus:ring-error/35'
				: 'border-base-300 focus:border-primary focus:ring-primary/25'}"
			type="password"
			autocomplete="new-password"
			bind:value={confirm}
			oninput={onConfirmInput}
		/>
		{#if fieldErrors.confirm}<span class="text-error text-xs">{fieldErrors.confirm}</span>{/if}
	</label>
	{#if formError}
		<p class="text-error text-sm" role="alert">{formError}</p>
	{/if}
	<Button type="submit" class="h-11 w-full justify-center" disabled={pending}
		>{pending ? 'Creating…' : 'Sign up'}</Button
	>
</form>
<p class="mt-4 text-sm">
	<a class="font-medium underline-offset-4 hover:underline" href="/login"
		>Already have an account?</a
	>
</p>
