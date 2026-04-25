<script lang="ts">
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import Button from '$lib/components/ui/Button.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import { postDisableOwnAccount } from '$lib/api/profile';
	import { signOutEverywhere } from '$lib/api/auth';
	import { getPublicSupportEmail } from '$lib/env/public';
	import { useProfile, useUpsertProfile } from '$lib/hooks/useProfile';
	import { profileSettingsSchema } from '$lib/schemas/profile';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';

	const profile = useProfile();
	const save = useUpsertProfile();

	const supportEmail = $derived(getPublicSupportEmail());

	let deleteModalOpen = $state(false);
	let deleteConfirmInput = $state('');
	let deleteModalError = $state('');
	let deleteBusy = $state(false);
	let deleteError = $state('');

	const canConfirmDelete = $derived(deleteConfirmInput.trim().toLowerCase() === 'delete');

	$effect(() => {
		if (!deleteModalOpen) {
			deleteConfirmInput = '';
			deleteModalError = '';
		}
	});

	let full_name = $state('');
	let professional_summary = $state('');
	let skillsText = $state('');
	let domain = $state('');
	let values_statement = $state('');
	let linkedin_url = $state('');
	let fieldErrors = $state<Record<string, string>>({});

function countSentences(text: string): number {
	return text
		.split(/[.!?]+/)
		.map((part) => part.trim())
		.filter(Boolean).length;
}

function rowsForText(text: string): number {
	const sentenceCount = countSentences(text);
	if (sentenceCount === 0 || sentenceCount <= 3) return 3;
	if (sentenceCount > 10) return 20;
	return 10;
}

	$effect(() => {
		const p = $profile.data;
		if (!p) return;
		full_name = p.full_name;
		professional_summary = p.professional_summary ?? '';
		skillsText = (p.skills ?? []).join(', ');
		domain = p.domain ?? '';
		values_statement = p.values_statement ?? '';
		linkedin_url = p.linkedin_url ?? '';
	});

	async function submit(e: Event): Promise<void> {
		e.preventDefault();
		fieldErrors = {};
		const parsed = profileSettingsSchema.safeParse({
			full_name,
			professional_summary,
			skillsText,
			domain,
			values_statement,
			linkedin_url
		});
		if (!parsed.success) {
			for (const iss of parsed.error.issues) {
				const k = String(iss.path[0] ?? 'form');
				fieldErrors = { ...fieldErrors, [k]: iss.message };
			}
			return;
		}
		const skills = parsed.data.skillsText
			? parsed.data.skillsText
					.split(',')
					.map((s) => s.trim())
					.filter(Boolean)
			: [];
		await get(save).mutateAsync({
			full_name: parsed.data.full_name,
			professional_summary: parsed.data.professional_summary || undefined,
			skills,
			domain: parsed.data.domain || undefined,
			values_statement: parsed.data.values_statement || undefined,
			linkedin_url: parsed.data.linkedin_url || undefined
		});
	}

	function clearField(key: string): void {
		fieldErrors = omitFieldErrors(fieldErrors, key);
	}

	function openDeleteModal(): void {
		deleteModalOpen = true;
	}

	async function confirmDeactivateAccount(): Promise<void> {
		if (!canConfirmDelete) return;
		deleteModalError = '';
		deleteError = '';
		deleteBusy = true;
		try {
			await postDisableOwnAccount();
			deleteModalOpen = false;
			await signOutEverywhere();
			await goto('/login');
		} catch (e) {
			const msg = e instanceof Error ? e.message : 'Something went wrong';
			deleteModalError = msg;
			deleteError = msg;
		} finally {
			deleteBusy = false;
		}
	}
</script>

{#if $profile.isPending}
	<p class="text-sm text-base-content/60">Loading profile…</p>
{:else if $profile.isError}
	<p class="text-sm text-error">Could not load profile.</p>
{:else}
	<form class="w-full space-y-4" onsubmit={submit}>
		<label class="form-control w-full md:w-1/3">
			<span class="label-text font-medium">Full name</span>
			<input
				class="input input-bordered rounded-xl border-base-300 bg-base-200"
				bind:value={full_name}
			/>
			{#if fieldErrors.full_name}<span class="label-text-alt text-error"
					>{fieldErrors.full_name}</span
				>{/if}
		</label>
		<label class="form-control">
			<span class="label-text font-medium">Summary</span>
			<textarea
				class="textarea textarea-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.professional_summary
					? 'textarea-error'
					: ''}"
				rows={rowsForText(professional_summary)}
				bind:value={professional_summary}
				oninput={() => clearField('professional_summary')}
			></textarea>
			{#if fieldErrors.professional_summary}
				<span class="label-text-alt text-error">{fieldErrors.professional_summary}</span>
			{/if}
		</label>
		<label class="form-control">
			<span class="label-text font-medium">Skills (comma-separated)</span>
			<input
				class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.skillsText
					? 'input-error'
					: ''}"
				bind:value={skillsText}
				oninput={() => clearField('skillsText')}
			/>
			{#if fieldErrors.skillsText}
				<span class="label-text-alt text-error">{fieldErrors.skillsText}</span>
			{/if}
		</label>
		<label class="form-control">
			<span class="label-text font-medium">Domain</span>
			<input
				class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.domain
					? 'input-error'
					: ''}"
				bind:value={domain}
				oninput={() => clearField('domain')}
			/>
			{#if fieldErrors.domain}<span class="label-text-alt text-error">{fieldErrors.domain}</span>{/if}
		</label>
		<label class="form-control">
			<span class="label-text font-medium">Values</span>
			<textarea
				class="textarea textarea-bordered rounded-xl border-base-300 bg-base-200"
				rows={rowsForText(values_statement)}
				bind:value={values_statement}
			></textarea>
		</label>
		<label class="form-control">
			<span class="label-text font-medium">LinkedIn URL</span>
			<input
				class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.linkedin_url
					? 'input-error'
					: ''}"
				placeholder="https://www.linkedin.com/in/your-handle"
				bind:value={linkedin_url}
				oninput={() => clearField('linkedin_url')}
			/>
			{#if fieldErrors.linkedin_url}
				<span class="label-text-alt text-error">{fieldErrors.linkedin_url}</span>
			{/if}
		</label>
		<Button type="submit" disabled={$save.isPending}
			>{$save.isPending ? 'Saving…' : 'Save profile'}</Button
		>
	</form>
	<div class="divider"></div>
	<div class="space-y-2">
		<h3 class="text-sm font-medium text-error">Danger zone</h3>
		<p class="text-sm text-base-content/70">
			Deactivate your account. Your session will end immediately.
		</p>
		{#if deleteError}<p class="text-sm text-error">{deleteError}</p>{/if}
		<Button
			type="button"
			variant="outline"
			class="btn-error border-error text-error hover:bg-error/10"
			disabled={deleteBusy}
			onclick={openDeleteModal}
		>
			Delete profile
		</Button>
	</div>

	<Modal bind:open={deleteModalOpen} title="Deactivate your account?">
		{#snippet children()}
			<div class="space-y-3 text-sm text-base-content/90">
				<p>
					This only <strong>disables</strong> your Kaziro account. You will be signed out and will
					not be able to use the app until support turns your access back on. Your profile and
					related data stay in our systems unless you ask for a full deletion separately.
				</p>
				<p>
					If you want <strong>all of your data permanently deleted</strong>, email the administrator
					{#if supportEmail}
						at
						<a class="link link-primary font-medium" href="mailto:{supportEmail}">{supportEmail}</a>.
					{:else}
						(ask your organization for the right contact address).
					{/if}
				</p>
				<label class="form-control w-full">
					<span class="label-text font-medium"
						>Type <span class="font-mono text-error">delete</span> to confirm</span
					>
					<input
						class="input input-bordered rounded-xl border-base-300 bg-base-200"
						type="text"
						autocomplete="off"
						placeholder="delete"
						bind:value={deleteConfirmInput}
						aria-invalid={deleteConfirmInput.length > 0 && !canConfirmDelete}
					/>
				</label>
				{#if deleteModalError}
					<p class="text-sm text-error">{deleteModalError}</p>
				{/if}
			</div>
		{/snippet}
		{#snippet footer()}
			<button type="button" class="btn btn-ghost rounded-xl" onclick={() => (deleteModalOpen = false)}>
				Cancel
			</button>
			<button
				type="button"
				class="btn btn-error rounded-xl"
				disabled={deleteBusy || !canConfirmDelete}
				onclick={() => void confirmDeactivateAccount()}
			>
				{deleteBusy ? 'Deactivating…' : 'Deactivate account'}
			</button>
		{/snippet}
	</Modal>
{/if}
