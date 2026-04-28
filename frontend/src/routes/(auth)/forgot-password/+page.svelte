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
	<p class="text-base-content/80 text-sm">
		If an account exists for that email, you will receive recovery instructions shortly.
	</p>
{:else}
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
		<Button type="submit" class="h-11 w-full justify-center" disabled={pending}
			>{pending ? 'Sending…' : 'Send reset link'}</Button
		>
	</form>
{/if}
<p class="mt-4 text-sm">
	<a class="font-medium underline-offset-4 hover:underline" href="/login">Back to log in</a>
</p>
