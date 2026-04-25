<script lang="ts">
	import { forgotSchema } from '$lib/schemas/auth';
	import { supabase } from '$lib/supabase';
	import Button from '$lib/components/ui/Button.svelte';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';

	let email = $state('');
	let fieldErrors = $state<Record<string, string>>({});
	let done = $state(false);
	let pending = $state(false);

	async function submit(e: Event): Promise<void> {
		e.preventDefault();
		fieldErrors = {};
		const parsed = forgotSchema.safeParse({ email });
		if (!parsed.success) {
			for (const iss of parsed.error.issues) {
				const k = String(iss.path[0] ?? 'form');
				fieldErrors = { ...fieldErrors, [k]: iss.message };
			}
			return;
		}
		pending = true;
		const { error } = await supabase.auth.resetPasswordForEmail(parsed.data.email, {
			redirectTo: `${typeof window !== 'undefined' ? window.location.origin : ''}/login`
		});
		pending = false;
		if (error) {
			fieldErrors = { ...fieldErrors, email: error.message };
			return;
		}
		done = true;
	}

	function onEmailInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'email');
	}
</script>

<svelte:head>
	<title>Forgot password — Kaziro</title>
</svelte:head>

<h1 class="mb-4 text-xl font-semibold">Reset password</h1>
{#if done}
	<p class="text-sm text-base-content/80">
		If an account exists for that email, you will receive recovery instructions shortly.
	</p>
{:else}
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
		<Button type="submit" disabled={pending}>{pending ? 'Sending…' : 'Send reset link'}</Button>
	</form>
{/if}
<p class="mt-4 text-sm">
	<a class="link font-medium" href="/login">Back to log in</a>
</p>
