<script lang="ts">
	import { get } from 'svelte/store';
	import Modal from '$lib/components/ui/Modal.svelte';
	import { ApiError } from '$lib/api/errors';
	import { FETCH_CRON_DAILY } from '$lib/constants/fetchSchedule';
	import {
		useCreateJobConfig,
		useSchedulePresets,
		useUpdateJobConfig
	} from '$lib/hooks/useJobConfig';
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

<Modal bind:open {title} boxClass="max-w-lg">
	<form id="job-config-editor-form" class="space-y-4" onsubmit={onSubmit}>
		{#if fieldErrors.form}
			<p class="text-error text-sm" role="alert">{fieldErrors.form}</p>
		{/if}
		<label class="block space-y-1.5">
			<span class="text-sm font-medium">Config name (optional)</span>
			<input
				class="bg-base-200 text-base-content placeholder:text-base-content/45 block w-full rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none {fieldErrors.name
					? 'border-error focus:ring-error/35'
					: 'border-base-300 focus:border-primary focus:ring-primary/25'}"
				bind:value={name}
				oninput={onNameInput}
			/>
			{#if fieldErrors.name}<span class="text-error text-xs">{fieldErrors.name}</span>{/if}
		</label>
		<label class="block space-y-1.5">
			<span class="text-sm font-medium">Keywords (comma-separated)</span>
			<input
				class="bg-base-200 text-base-content placeholder:text-base-content/45 block w-full rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none {fieldErrors.keywordsText
					? 'border-error focus:ring-error/35'
					: 'border-base-300 focus:border-primary focus:ring-primary/25'}"
				bind:value={keywordsText}
				oninput={onKeywordsInput}
			/>
			{#if fieldErrors.keywordsText}
				<span class="text-error text-xs">{fieldErrors.keywordsText}</span>
			{/if}
		</label>
		<label class="block space-y-1.5">
			<span class="text-sm font-medium">Location</span>
			<input
				class="bg-base-200 text-base-content placeholder:text-base-content/45 block w-full rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none {fieldErrors.location
					? 'border-error focus:ring-error/35'
					: 'border-base-300 focus:border-primary focus:ring-primary/25'}"
				bind:value={location}
				oninput={onLocationInput}
			/>
			{#if fieldErrors.location}
				<span class="text-error text-xs">{fieldErrors.location}</span>
			{/if}
		</label>
		<div class="block space-y-1.5">
			<label
				class="bg-base-200 border-base-300 flex w-full items-start gap-3 rounded-xl border px-3 py-2.5"
			>
				<input
					type="checkbox"
					class="border-base-400 bg-base-100 text-primary focus:ring-primary/30 mt-0.5 h-4 w-4 rounded focus:ring-2"
					bind:checked={remote_only}
				/>
				<div class="space-y-0.5">
					<span class="text-sm font-medium">Remote only</span>
					<p class="text-base-content/70 text-xs">Only include jobs that are fully remote.</p>
				</div>
			</label>
		</div>
		<div class="grid gap-4 sm:grid-cols-2">
			<label class="block space-y-1.5">
				<span class="text-sm font-medium">Salary min</span>
				<input
					class="bg-base-200 text-base-content placeholder:text-base-content/45 block w-full rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none {fieldErrors.salary_min
						? 'border-error focus:ring-error/35'
						: 'border-base-300 focus:border-primary focus:ring-primary/25'}"
					type="text"
					inputmode="numeric"
					pattern="[0-9]*"
					autocomplete="off"
					maxlength="9"
					value={salaryMinInput}
					oninput={onSalaryMinInput}
				/>
				{#if fieldErrors.salary_min}
					<span class="text-error text-xs">{fieldErrors.salary_min}</span>
				{/if}
			</label>
			<label class="block space-y-1.5">
				<span class="text-sm font-medium">Salary max</span>
				<input
					class="bg-base-200 text-base-content placeholder:text-base-content/45 block w-full rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none {fieldErrors.salary_max
						? 'border-error focus:ring-error/35'
						: 'border-base-300 focus:border-primary focus:ring-primary/25'}"
					type="text"
					inputmode="numeric"
					pattern="[0-9]*"
					autocomplete="off"
					maxlength="9"
					value={salaryMaxInput}
					oninput={onSalaryMaxInput}
				/>
				{#if fieldErrors.salary_max}
					<span class="text-error text-xs">{fieldErrors.salary_max}</span>
				{/if}
			</label>
		</div>
		<label class="block space-y-1.5">
			<span class="text-sm font-medium">Fetch schedule</span>
			{#if $presets.isPending}
				<select
					class="bg-base-200 text-base-content border-base-300 block w-full cursor-not-allowed rounded-xl border px-3 py-2.5 opacity-60"
					disabled
				>
					<option>Loading…</option>
				</select>
			{:else if $presets.isError}
				<p class="text-error text-sm">Could not load schedules.</p>
			{:else if $presets.data}
				<select
					class="bg-base-200 text-base-content block w-full rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none {fieldErrors.fetch_schedule_cron
						? 'border-error focus:ring-error/35'
						: 'border-base-300 focus:border-primary focus:ring-primary/25'}"
					bind:value={fetch_schedule_cron}
					onchange={onFetchScheduleChange}
				>
					{#each $presets.data as p (p.id)}
						<option value={p.fetch_schedule_cron}>{p.label}</option>
					{/each}
				</select>
			{/if}
			{#if fieldErrors.fetch_schedule_cron}
				<span class="text-error text-xs">{fieldErrors.fetch_schedule_cron}</span>
			{/if}
		</label>
	</form>
	{#snippet footer()}
		<button type="button" class="btn btn-ghost rounded-xl" onclick={() => (open = false)}
			>Cancel</button
		>
		<button
			type="submit"
			form="job-config-editor-form"
			class="btn btn-primary rounded-xl font-medium"
			disabled={saving ||
				$createMut.isPending ||
				$updateMut.isPending ||
				$presets.isPending ||
				$presets.isError}
		>
			{saving || $createMut.isPending || $updateMut.isPending ? 'Saving…' : 'Save'}
		</button>
	{/snippet}
</Modal>
