import Link from '@tiptap/extension-link';

export const CtrlKLink = Link.configure({
  autolink: true,
  HTMLAttributes: {
    target: '_blank',
    rel: 'noopener noreferrer',
  },
  linkOnPaste: true,
  openOnClick: false,
}).extend({
  addKeyboardShortcuts() {
    return {
      'Mod-k': () => {
        // Check if there is a selection
        if (this.editor.state.selection.empty) return true;

        // Get previous url
        const previousUrl = this.editor.isActive('link')
          ? this.editor.getAttributes('link').href
          : '';

        // Edit url
        const newUrl = window.prompt('URL', previousUrl);

        // If cancel, do nothing
        if (newUrl === null) return true;

        // If empty url, remove preexisting url
        if (newUrl === '') {
          if (previousUrl !== '')
            this.editor.chain().focus().extendMarkRange('link').unsetLink().run();
          return true;
        }

        // Non-empty string is url
        this.editor.chain().focus().extendMarkRange('link').setLink({ href: newUrl }).run();
        return true;
      },
    };
  },
});