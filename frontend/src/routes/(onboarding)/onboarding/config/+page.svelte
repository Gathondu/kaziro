<script lang="ts">
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import WizardProgress from '$lib/components/onboarding/WizardProgress.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { FETCH_CRON_DAILY } from '$lib/constants/fetchSchedule';
	import { useCreateJobConfig, useRunJobConfigPipeline, useSchedulePresets } from '$lib/hooks/useJobConfig';
	import { jobConfigFormSchema } from '$lib/schemas/jobConfig';
	import { clearOnboardingDraft, saveOnboardingDraft } from '$lib/utils/onboarding';

	let name = $state('');
	let keywordsText = $state('');
	let location = $state('');
	let remote_only = $state(false);
	let salary_min = $state<number | ''>('');
	let salary_max = $state<number | ''>('');
	let fetch_schedule_cron = $state(FETCH_CRON_DAILY);
	let fieldErrors = $state<Record<string, string>>({});

	const presets = useSchedulePresets();
	const createCfg = useCreateJobConfig();
	const runPipe = useRunJobConfigPipeline();

	async function finish(e: Event): Promise<void> {
		e.preventDefault();
		fieldErrors = {};
		const parsed = jobConfigFormSchema.safeParse({
			name,
			keywordsText,
			location,
			remote_only,
			salary_min: salary_min === '' ? null : salary_min,
			salary_max: salary_max === '' ? null : salary_max,
			fetch_schedule_cron
		});
		if (!parsed.success) {
			for (const iss of parsed.error.issues) {
				const k = String(iss.path[0] ?? 'form');
				fieldErrors = { ...fieldErrors, [k]: iss.message };
			}
			return;
		}
		const keywords = parsed.data.keywordsText
			.split(',')
			.map((k) => k.trim())
			.filter(Boolean);
		const cfg = await get(createCfg).mutateAsync({
			name: parsed.data.name || null,
			keywords,
			location: parsed.data.location || null,
			remote_only: parsed.data.remote_only,
			salary_min: parsed.data.salary_min,
			salary_max: parsed.data.salary_max,
			fetch_schedule_cron: parsed.data.fetch_schedule_cron
		});
		saveOnboardingDraft({ step: 3, lastConfigId: cfg.id });
		await get(runPipe).mutateAsync(cfg.id);
		clearOnboardingDraft();
		await goto('/dashboard');
	}
</script>

<svelte:head>
	<title>Onboarding — Job search</title>
</svelte:head>

<WizardProgress step={3} />
<h1 class="mb-2 text-xl font-semibold">First job search</h1>
<p class="mb-6 text-sm text-base-content/70">
	We will enqueue your first pipeline run so evaluations can start flowing in.
</p>
<form class="space-y-4" onsubmit={finish}>
	<label class="form-control">
		<span class="label-text font-medium">Config name (optional)</span>
		<input class="input input-bordered rounded-xl border-base-300 bg-base-200" bind:value={name} />
	</label>
	<label class="form-control">
		<span class="label-text font-medium">Keywords (comma-separated)</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.keywordsText
				? 'input-error'
				: ''}"
			bind:value={keywordsText}
		/>
		{#if fieldErrors.keywordsText}<span class="label-text-alt text-error"
				>{fieldErrors.keywordsText}</span
			>{/if}
	</label>
	<label class="form-control">
		<span class="label-text font-medium">Location</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200"
			bind:value={location}
		/>
	</label>
	<label class="label cursor-pointer justify-start gap-3">
		<input type="checkbox" class="checkbox-primary checkbox" bind:checked={remote_only} />
		<span class="font-medium">Remote only</span>
	</label>
	<div class="grid gap-4 sm:grid-cols-2">
		<label class="form-control">
			<span class="label-text font-medium">Salary min</span>
			<input
				class="input input-bordered rounded-xl border-base-300 bg-base-200"
				type="number"
				bind:value={salary_min}
			/>
		</label>
		<label class="form-control">
			<span class="label-text font-medium">Salary max</span>
			<input
				class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.salary_max
					? 'input-error'
					: ''}"
				type="number"
				bind:value={salary_max}
			/>
			{#if fieldErrors.salary_max}<span class="label-text-alt text-error"
					>{fieldErrors.salary_max}</span
				>{/if}
		</label>
	</div>
	<label class="form-control">
		<span class="label-text font-medium">Fetch schedule</span>
		{#if $presets.isPending}
			<select class="select select-bordered rounded-xl border-base-300 bg-base-200" disabled>
				<option>Loading…</option>
			</select>
		{:else if $presets.isError}
			<p class="text-sm text-error">Could not load schedules. Refresh and try again.</p>
		{:else if $presets.data}
			<select
				class="select select-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.fetch_schedule_cron
					? 'select-error'
					: ''}"
				bind:value={fetch_schedule_cron}
			>
				{#each $presets.data as p (p.id)}
					<option value={p.fetch_schedule_cron}>{p.label}</option>
				{/each}
			</select>
			<span class="label-text-alt text-base-content/60">Runs are scheduled in UTC.</span>
		{/if}
		{#if fieldErrors.fetch_schedule_cron}
			<span class="label-text-alt text-error">{fieldErrors.fetch_schedule_cron}</span>
		{/if}
	</label>
	<div class="flex gap-3">
		<Button type="button" variant="outline" onclick={() => goto('/onboarding/cv')}>Back</Button>
		<Button
			type="submit"
			disabled={$createCfg.isPending ||
				$runPipe.isPending ||
				$presets.isPending ||
				$presets.isError}
		>
			{$createCfg.isPending || $runPipe.isPending ? 'Finishing…' : 'Finish setup'}
		</Button>
	</div>
</form>
