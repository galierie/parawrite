<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Editor } from '@tiptap/core';
  import { StarterKit, type StarterKitOptions } from '@tiptap/starter-kit';
  import { CtrlKLink } from './extensions/ctrl-k-link';

  interface EditorState {
    editor: Editor | null;
  }

  let editorState: EditorState = $state({ editor: null });
  let editorElement: HTMLDivElement | null = $state(null);

  const starterKitExtensionsConfig: Partial<StarterKitOptions> = {
    blockquote: false,
    bulletList: {
      HTMLAttributes: {
        class: 'list-disc pl-6',
      },
    },
    dropcursor: false,
    horizontalRule: false,
    link: false,
    orderedList: {
      HTMLAttributes: {
        class: 'list-decimal pl-6',
      },
    },
  };

  function mountEditor() {
    editorState.editor = new Editor({
      element: editorElement,
      extensions: [
        StarterKit.configure(starterKitExtensionsConfig),
        CtrlKLink.configure({
          HTMLAttributes: {
            class: 'underline',
          }
        }),
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
