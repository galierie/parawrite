<script lang="ts">
    import { EditorState } from '@tiptap/pm/state';
    import { EditorView } from '@tiptap/pm/view';
    import { TextEditorComponent } from '$lib/features/text-editor';

    let doc: EditorState['doc'] = $state({} as EditorState['doc']);
    let view: EditorView = $state({} as EditorView);
</script>

<div class="mb-24 text-center text-grandis-100">
    <h1 class="font-satisfy text-6xl sm:text-8xl">Parawrite</h1>
    <p class="text-base sm:text-xl">Your personal writing companion</p>
</div>

<div class="flex justify-center">
    <div
        class="relative min-h-[297mm] w-[210mm] bg-white p-6 text-black shadow-lg shadow-black sm:p-12 lg:p-24"
    >
        <TextEditorComponent bind:doc bind:view />
    </div>
</div>
