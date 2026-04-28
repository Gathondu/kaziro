<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { get } from 'svelte/store';
	import { useQueryClient } from '@tanstack/svelte-query';
	import Button from '$lib/components/ui/Button.svelte';
	import { putProfile, uploadCvPdf } from '$lib/api/profile';
	import { FETCH_CRON_DAILY } from '$lib/constants/fetchSchedule';
	import {
		useCreateJobConfig,
		useRunJobConfigPipeline,
		useSchedulePresets
	} from '$lib/hooks/useJobConfig';
	import { jobConfigFormSchema } from '$lib/schemas/jobConfig';
	import {
		clearOnboardingDraft,
		loadOnboardingDraft,
		resumeOnboardingPath,
		saveOnboardingDraft
	} from '$lib/utils/onboarding';
	import {
		clearOnboardingPendingCv,
		getOnboardingPendingCv
	} from '$lib/utils/onboarding-pending-cv';
	import { validateProfileDraftForSubmit } from '$lib/utils/onboarding-profile.functions';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';
	import { sanitizeSalaryInput } from '$lib/utils/salary-input.utils';

	let name = $state('');
	let keywordsText = $state('');
	let location = $state('');
	let remote_only = $state(false);
	let salaryMinInput = $state('');
	let salaryMaxInput = $state('');
	let fetch_schedule_cron = $state(FETCH_CRON_DAILY);
	let fieldErrors = $state<Record<string, string>>({});
	let finishing = $state(false);

	const presets = useSchedulePresets();
	const createCfg = useCreateJobConfig();
	const runPipe = useRunJobConfigPipeline();
	const qc = useQueryClient();

	$effect(() => {
		if (!browser) return;
		const path = get(page).url.pathname;
		const d = loadOnboardingDraft();
		const want = resumeOnboardingPath(d);
		if (want !== path) void goto(want);
	});

	async function finish(e: Event): Promise<void> {
		e.preventDefault();
		fieldErrors = {};
		const parsed = jobConfigFormSchema.safeParse({
			name,
			keywordsText,
			location,
			remote_only,
			salary_min: salaryMinInput.trim() === '' ? null : salaryMinInput,
			salary_max: salaryMaxInput.trim() === '' ? null : salaryMaxInput,
			fetch_schedule_cron
		});
		if (!parsed.success) {
			for (const iss of parsed.error.issues) {
				const k = String(iss.path[0] ?? 'form');
				fieldErrors = { ...fieldErrors, [k]: iss.message };
			}
			return;
		}

		const draft = loadOnboardingDraft();
		const profileValidated = validateProfileDraftForSubmit(draft?.profile);
		if (!profileValidated.ok) {
			fieldErrors = {
				form: 'Your profile data is incomplete. Use Back to fix earlier steps.'
			};
			return;
		}

		const keywords = parsed.data.keywordsText
			.split(',')
			.map((k) => k.trim())
			.filter(Boolean);

		finishing = true;
		try {
			const profile = await putProfile(profileValidated.body);
			qc.setQueryData(['profile'], profile);

			const cvFile = getOnboardingPendingCv();
			if (cvFile) {
				await uploadCvPdf(cvFile);
				clearOnboardingPendingCv();
				await qc.invalidateQueries({ queryKey: ['profile'] });
			}

			const cfg = await get(createCfg).mutateAsync({
				name: parsed.data.name || null,
				keywords,
				location: parsed.data.location || null,
				remote_only: parsed.data.remote_only,
				salary_min: parsed.data.salary_min,
				salary_max: parsed.data.salary_max,
				fetch_schedule_cron: parsed.data.fetch_schedule_cron
			});
			saveOnboardingDraft({
				step: 3,
				lastConfigId: cfg.id,
				profile: draft?.profile ?? {}
			});
			await get(runPipe).mutateAsync(cfg.id);
			clearOnboardingDraft();
			await goto('/dashboard');
		} catch {
			fieldErrors = {
				form: 'Could not finish setup. Check your connection and try again.'
			};
		} finally {
			finishing = false;
		}
	}

	function clearSalaryFieldErrors(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'salary_min', 'salary_max');
	}

	function onKeywordsInput(): void {
		let next = omitFieldErrors(fieldErrors, 'keywordsText');
		if (next.form?.startsWith('Could not finish')) {
			next = omitFieldErrors(next, 'form');
		}
		fieldErrors = next;
	}

	function onNameInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'name');
	}

	function onLocationInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'location');
	}

	function onFetchScheduleChange(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'fetch_schedule_cron');
	}

	function onSalaryMinInput(e: Event): void {
		const el = e.currentTarget as HTMLInputElement;
		const next = sanitizeSalaryInput(el.value);
		salaryMinInput = next;
		if (el.value !== next) el.value = next;
		clearSalaryFieldErrors();
	}

	function onSalaryMaxInput(e: Event): void {
		const el = e.currentTarget as HTMLInputElement;
		const next = sanitizeSalaryInput(el.value);
		salaryMaxInput = next;
		if (el.value !== next) el.value = next;
		clearSalaryFieldErrors();
	}
</script>

<svelte:head>
	<title>Onboarding — Job search</title>
</svelte:head>

<h1 class="mb-2 text-xl font-semibold">First job search</h1>
<p class="text-base-content/70 mb-6 text-sm">
	We will enqueue your first pipeline run so evaluations can start flowing in.
</p>
<form class="space-y-4" onsubmit={finish}>
	{#if fieldErrors.form}
		<p class="text-error text-sm" role="alert">{fieldErrors.form}</p>
	{/if}
	<label class="form-control">
		<span class="label-text font-medium">Config name (optional)</span>
		<input
			class="input input-bordered border-base-300 bg-base-200 rounded-xl"
			bind:value={name}
			oninput={onNameInput}
		/>
	</label>
	<label class="form-control">
		<span class="label-text font-medium">Keywords (comma-separated)</span>
		<input
			class="input input-bordered border-base-300 bg-base-200 rounded-xl {fieldErrors.keywordsText
				? 'input-error'
				: ''}"
			bind:value={keywordsText}
			oninput={onKeywordsInput}
		/>
		{#if fieldErrors.keywordsText}<span class="label-text-alt text-error"
				>{fieldErrors.keywordsText}</span
			>{/if}
	</label>
	<label class="form-control">
		<span class="label-text font-medium">Location</span>
		<input
			class="input input-bordered border-base-300 bg-base-200 rounded-xl"
			bind:value={location}
			oninput={onLocationInput}
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
				class="input input-bordered border-base-300 bg-base-200 rounded-xl {fieldErrors.salary_min
					? 'input-error'
					: ''}"
				type="text"
				inputmode="numeric"
				pattern="[0-9]*"
				autocomplete="off"
				maxlength="9"
				value={salaryMinInput}
				oninput={onSalaryMinInput}
			/>
			{#if fieldErrors.salary_min}<span class="label-text-alt text-error"
					>{fieldErrors.salary_min}</span
				>{/if}
		</label>
		<label class="form-control">
			<span class="label-text font-medium">Salary max</span>
			<input
				class="input input-bordered border-base-300 bg-base-200 rounded-xl {fieldErrors.salary_max
					? 'input-error'
					: ''}"
				type="text"
				inputmode="numeric"
				pattern="[0-9]*"
				autocomplete="off"
				maxlength="9"
				value={salaryMaxInput}
				oninput={onSalaryMaxInput}
			/>
			{#if fieldErrors.salary_max}<span class="label-text-alt text-error"
					>{fieldErrors.salary_max}</span
				>{/if}
		</label>
	</div>
	<label class="form-control">
		<span class="label-text font-medium">Fetch schedule</span>
		{#if $presets.isPending}
			<select class="select select-bordered border-base-300 bg-base-200 rounded-xl" disabled>
				<option>Loading…</option>
			</select>
		{:else if $presets.isError}
			<p class="text-error text-sm">Could not load schedules. Refresh and try again.</p>
		{:else if $presets.data}
			<select
				class="select select-bordered border-base-300 bg-base-200 rounded-xl {fieldErrors.fetch_schedule_cron
					? 'select-error'
					: ''}"
				bind:value={fetch_schedule_cron}
				onchange={onFetchScheduleChange}
			>
				{#each $presets.data as p (p.id)}
					<option value={p.fetch_schedule_cron}>{p.label}</option>
				{/each}
			</select>
		{/if}
		{#if fieldErrors.fetch_schedule_cron}
			<span class="label-text-alt text-error">{fieldErrors.fetch_schedule_cron}</span>
		{/if}
	</label>
	<Button
		type="submit"
		disabled={finishing ||
			$createCfg.isPending ||
			$runPipe.isPending ||
			$presets.isPending ||
			$presets.isError}
	>
		{finishing || $createCfg.isPending || $runPipe.isPending ? 'Finishing…' : 'Finish setup'}
	</Button>
</form>
