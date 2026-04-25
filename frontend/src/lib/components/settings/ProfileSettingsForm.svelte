<script lang="ts">
	import { get } from 'svelte/store';
	import Button from '$lib/components/ui/Button.svelte';
	import { useProfile, useUpsertProfile } from '$lib/hooks/useProfile';
	import { profileSettingsSchema } from '$lib/schemas/profile';

	const profile = useProfile();
	const save = useUpsertProfile();

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
				class="textarea textarea-bordered rounded-xl border-base-300 bg-base-200"
				rows={rowsForText(professional_summary)}
				bind:value={professional_summary}
			></textarea>
		</label>
		<label class="form-control">
			<span class="label-text font-medium">Skills (comma-separated)</span>
			<input
				class="input input-bordered rounded-xl border-base-300 bg-base-200"
				bind:value={skillsText}
			/>
		</label>
		<label class="form-control">
			<span class="label-text font-medium">Domain</span>
			<input class="input input-bordered rounded-xl border-base-300 bg-base-200" bind:value={domain} />
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
				class="input input-bordered rounded-xl border-base-300 bg-base-200"
				placeholder="https://www.linkedin.com/in/your-handle"
				bind:value={linkedin_url}
			/>
			{#if fieldErrors.linkedin_url}
				<span class="label-text-alt text-error">{fieldErrors.linkedin_url}</span>
			{/if}
		</label>
		<Button type="submit" disabled={$save.isPending}
			>{$save.isPending ? 'Saving…' : 'Save profile'}</Button
		>
	</form>
{/if}
