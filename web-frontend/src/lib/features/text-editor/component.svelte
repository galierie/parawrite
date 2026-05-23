<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Editor } from '@tiptap/core';
  import { StarterKit } from '@tiptap/starter-kit';

  interface EditorState {
    editor: Editor | null;
  }

  let editorState: EditorState = $state({ editor: null });
  let editorElement: HTMLDivElement | null = $state(null);

  function mountEditor() {
    editorState.editor = new Editor({
      element: editorElement,
      extensions: [
        StarterKit,
      ],
      editorProps: {
        attributes: {
          class: 'focus:outline-none focus:ring-0 h-full w-full',
        }
      },
      onTransaction: ({ editor }) => {
        // Update the state signal to force a re-render
        editorState = { editor }
      },
    });
  }

  onMount(() => {
    if (editorElement !== null)
      mountEditor();
  });

  onDestroy(() => {
    if (editorState.editor !== null)
      editorState.editor.destroy();
  });
</script>

<div class="relative h-full w-full">
  <div class="h-full w-full" bind:this={editorElement}></div>
</div>
