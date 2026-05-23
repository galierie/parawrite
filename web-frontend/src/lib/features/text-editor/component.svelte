<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Editor } from '@tiptap/core';
  import { StarterKit, type StarterKitOptions } from '@tiptap/starter-kit';
  import { CtrlKLink, setLink } from './extensions/ctrl-k-link';
  import Icon from '@iconify/svelte';

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

{#snippet formatBtn(tablerIcon: string, onclick: () => void)}
  <button {onclick} class="mx-2">
    <Icon icon={`tabler:${tablerIcon}`} class="h-5 w-5" />
  </button>
{/snippet}

<div class="relative h-full w-full">
  {#if editorState.editor}
    {@const editor = editorState.editor}

    <div class="flex justify-center items-center">
      <div class="flex justify-center items-center relative -top-7 h-7 w-fit shadow-sm rounded-sm">
        {@render formatBtn('arrow-back-up', () => (editor.chain().focus().undo().run()))}
        {@render formatBtn('arrow-forward-up', () => (editor.chain().focus().redo().run()))}
        <Icon icon="tabler:minus-vertical" class="text-gray-400 h-6 w-6" />
        {@render formatBtn('bold', () => (editor.chain().focus().toggleBold().run()))}
        {@render formatBtn('italic', () => (editor.chain().focus().toggleItalic().run()))}
        {@render formatBtn('underline', () => (editor.chain().focus().toggleUnderline().run()))}
        {@render formatBtn('strikethrough', () => (editor.chain().focus().toggleStrike().run()))}
        <Icon icon="tabler:minus-vertical" class="text-gray-400 h-6 w-6" />
        {@render formatBtn('code', () => (editor.chain().focus().toggleCode().run()))}
        {@render formatBtn('link', () => (setLink(editor)))}
        <Icon icon="tabler:minus-vertical" class="text-gray-400 h-6 w-6" />
        {@render formatBtn('list', () => (editor.chain().focus().toggleBulletList().run()))}
        {@render formatBtn('list-numbers', () => (editor.chain().focus().toggleOrderedList().run()))}
      </div>
    </div>
  {/if}
  <div class="h-full w-full" bind:this={editorElement}></div>
</div>
