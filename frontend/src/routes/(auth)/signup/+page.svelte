<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { signupSchema } from '$lib/schemas/auth';
	import { getUser, isAuthReady } from '$lib/stores/auth';
	import { supabase } from '$lib/supabase';
	import Button from '$lib/components/ui/Button.svelte';
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
</script>

<svelte:head>
	<title>Sign up — Kaziro</title>
</svelte:head>

<h1 class="mb-4 text-xl font-semibold">Create your account</h1>
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
			autocomplete="new-password"
			bind:value={password}
		/>
		{#if fieldErrors.password}<span class="label-text-alt text-error">{fieldErrors.password}</span
			>{/if}
	</label>
	<label class="form-control">
		<span class="label-text font-medium">Confirm password</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.confirm
				? 'input-error'
				: ''}"
			type="password"
			autocomplete="new-password"
			bind:value={confirm}
		/>
		{#if fieldErrors.confirm}<span class="label-text-alt text-error">{fieldErrors.confirm}</span
			>{/if}
	</label>
	{#if formError}
		<p class="text-sm text-error" role="alert">{formError}</p>
	{/if}
	<Button type="submit" disabled={pending}>{pending ? 'Creating…' : 'Sign up'}</Button>
</form>
<p class="mt-4 text-sm">
	<a class="link font-medium" href="/login">Already have an account?</a>
</p>
