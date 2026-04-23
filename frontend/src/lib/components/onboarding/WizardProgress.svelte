<script lang="ts">
	const { step }: { step: 1 | 2 | 3 } = $props();

	const steps = [
		{ n: 1 as const, label: 'Profile', href: '/onboarding/profile' },
		{ n: 2 as const, label: 'CV', href: '/onboarding/cv' },
		{ n: 3 as const, label: 'Job search', href: '/onboarding/config' }
	];
</script>

<nav aria-label="Onboarding progress" class="mb-6 flex gap-2">
	{#each steps as s (s.n)}
		<a
			href={s.href}
			class="flex flex-1 items-center justify-center rounded-xl border px-3 py-2 text-center text-sm font-medium {step ===
			s.n
				? 'border-primary bg-primary text-primary-content'
				: step > s.n
					? 'border-success/40 bg-base-200 text-base-content'
					: 'border-base-300 bg-base-100 text-base-content/60'}"
		>
			{s.n}. {s.label}
		</a>
	{/each}
</nav>
