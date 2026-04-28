<script lang="ts">
	let {
		value = $bindable(''),
		disabled = false
	}: {
		value?: string;
		disabled?: boolean;
	} = $props();

	let host = $state<HTMLDivElement | null>(null);
	let editor = $state<import('@tiptap/core').Editor | null>(null);
	let mounted = $state(false);

	$effect(() => {
		if (!host || mounted || disabled) return;
		let cancelled = false;
		void (async () => {
			const [{ Editor }, { default: StarterKit }] = await Promise.all([
				import('@tiptap/core'),
				import('@tiptap/starter-kit')
			]);
			if (cancelled || !host) return;
			const ed = new Editor({
				element: host,
				extensions: [StarterKit],
				content: value || '<p></p>',
				editable: !disabled,
				onUpdate: () => {
					value = ed.getHTML();
				}
			});
			editor = ed;
			mounted = true;
		})();
		return () => {
			cancelled = true;
			editor?.destroy();
			editor = null;
			mounted = false;
		};
	});
</script>

<div
	bind:this={host}
	class="border-base-300 bg-base-100 min-h-64 rounded-xl border p-3 text-sm leading-relaxed"
	role="textbox"
	aria-label="Cover letter editor"
></div>
