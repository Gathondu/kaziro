<script lang="ts">
	import { get } from 'svelte/store';
	import Modal from '$lib/components/ui/Modal.svelte';
	import { ApiError } from '$lib/api/errors';
	import { FETCH_CRON_DAILY } from '$lib/constants/fetchSchedule';
	import { useCreateJobConfig, useSchedulePresets, useUpdateJobConfig } from '$lib/hooks/useJobConfig';
	import { jobConfigFormSchema } from '$lib/schemas/jobConfig';
	import type { JobConfig } from '$lib/types/jobConfig';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';
	import { sanitizeSalaryInput } from '$lib/utils/salary-input.utils';
	import { toast } from '$lib/stores/toast';

	let {
		open = $bindable(false),
		mode,
		config
	}: {
		open?: boolean;
		mode: 'create' | 'edit';
		config: JobConfig | null;
	} = $props();

	let name = $state('');
	let keywordsText = $state('');
	let location = $state('');
	let remote_only = $state(false);
	let salaryMinInput = $state('');
	let salaryMaxInput = $state('');
	let fetch_schedule_cron = $state<string>(FETCH_CRON_DAILY);
	let fieldErrors = $state<Record<string, string>>({});
	let saving = $state(false);

	const createMut = useCreateJobConfig();
	const updateMut = useUpdateJobConfig();
	const presets = useSchedulePresets();

	function seedFromProps(): void {
		fieldErrors = {};
		if (mode === 'edit' && config) {
			name = config.name ?? '';
			keywordsText = (config.keywords ?? []).join(', ');
			location = config.location ?? '';
			remote_only = config.remote_only;
			salaryMinInput = config.salary_min != null ? String(config.salary_min) : '';
			salaryMaxInput = config.salary_max != null ? String(config.salary_max) : '';
			fetch_schedule_cron = config.fetch_schedule_cron;
		} else {
			name = '';
			keywordsText = '';
			location = '';
			remote_only = false;
			salaryMinInput = '';
			salaryMaxInput = '';
			fetch_schedule_cron = FETCH_CRON_DAILY;
		}
	}

	$effect(() => {
		if (!open) return;
		void mode;
		void config?.id;
		seedFromProps();
	});

	function clearSalaryFieldErrors(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'salary_min', 'salary_max');
	}

	function onKeywordsInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'keywordsText');
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

	async function onSubmit(e: Event): Promise<void> {
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

		const keywords = parsed.data.keywordsText
			.split(',')
			.map((k) => k.trim())
			.filter(Boolean);

		const body = {
			name: parsed.data.name || null,
			keywords,
			location: parsed.data.location || null,
			remote_only: parsed.data.remote_only,
			salary_min: parsed.data.salary_min,
			salary_max: parsed.data.salary_max,
			fetch_schedule_cron: parsed.data.fetch_schedule_cron
		};

		saving = true;
		try {
			if (mode === 'create') {
				await get(createMut).mutateAsync(body);
				toast.success('Job config created.');
			} else if (config) {
				await get(updateMut).mutateAsync({ id: config.id, body });
				toast.success('Job config updated.');
			}
			open = false;
		} catch (err) {
			toast.error(err instanceof ApiError ? err.message : 'Could not save config');
		} finally {
			saving = false;
		}
	}

	const title = $derived(mode === 'create' ? 'New job config' : 'Edit job config');
</script>

<Modal bind:open title={title} boxClass="max-w-lg">
	{#snippet children()}
		<form id="job-config-editor-form" class="space-y-4" onsubmit={onSubmit}>
			{#if fieldErrors.form}
				<p class="text-sm text-error" role="alert">{fieldErrors.form}</p>
			{/if}
			<label class="form-control">
				<span class="label-text font-medium">Config name (optional)</span>
				<input
					class="input input-bordered rounded-xl border-base-300 bg-base-200"
					bind:value={name}
					oninput={onNameInput}
				/>
			</label>
			<label class="form-control">
				<span class="label-text font-medium">Keywords (comma-separated)</span>
				<input
					class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.keywordsText
						? 'input-error'
						: ''}"
					bind:value={keywordsText}
					oninput={onKeywordsInput}
				/>
				{#if fieldErrors.keywordsText}
					<span class="label-text-alt text-error">{fieldErrors.keywordsText}</span>
				{/if}
			</label>
			<label class="form-control">
				<span class="label-text font-medium">Location</span>
				<input
					class="input input-bordered rounded-xl border-base-300 bg-base-200"
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
						class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.salary_min
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
					{#if fieldErrors.salary_min}
						<span class="label-text-alt text-error">{fieldErrors.salary_min}</span>
					{/if}
				</label>
				<label class="form-control">
					<span class="label-text font-medium">Salary max</span>
					<input
						class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.salary_max
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
					{#if fieldErrors.salary_max}
						<span class="label-text-alt text-error">{fieldErrors.salary_max}</span>
					{/if}
				</label>
			</div>
			<label class="form-control">
				<span class="label-text font-medium">Fetch schedule</span>
				{#if $presets.isPending}
					<select class="select select-bordered rounded-xl border-base-300 bg-base-200" disabled>
						<option>Loading…</option>
					</select>
				{:else if $presets.isError}
					<p class="text-sm text-error">Could not load schedules.</p>
				{:else if $presets.data}
					<select
						class="select select-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.fetch_schedule_cron
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
		</form>
	{/snippet}
	{#snippet footer()}
		<button type="button" class="btn btn-ghost rounded-xl" onclick={() => (open = false)}>Cancel</button>
		<button
			type="submit"
			form="job-config-editor-form"
			class="btn btn-primary font-medium rounded-xl"
			disabled={
				saving ||
				$createMut.isPending ||
				$updateMut.isPending ||
				$presets.isPending ||
				$presets.isError
			}
		>
			{saving || $createMut.isPending || $updateMut.isPending ? 'Saving…' : 'Save'}
		</button>
	{/snippet}
</Modal>
