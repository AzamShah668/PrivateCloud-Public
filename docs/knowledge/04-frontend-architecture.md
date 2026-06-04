# Frontend Architecture

## Stack
- Vite + React + TypeScript
- Styling: Tailwind CSS + custom CSS variables (cyberpunk/Aether theme)
- Animation: motion/react (Framer Motion)
- State: React Query (TanStack Query) for server state
- Routing: React Router

## Key Components (VM Detail Page)
### VMDetailPage.tsx
- Main page for individual VM management
- Controls: ActionBar, ConsoleModal, GuacamoleModal, ResizeModal, DeleteConfirm
- Determines OS type via `isWindows` flag from vm.os_choice

### ActionBar.tsx
- Props: liveStatus, vmIP, onStart/Stop/Restart/Resize/Console/Delete, isPending
- **showConsole?: boolean** - conditionally renders Console button (Linux only)
- **showRemoteDesktop?: boolean** - conditionally renders Desktop button (Windows only)
- **FRAGILE**: This file has broken multiple times from hot-patching. Always verify syntax.

### ConsoleModal.tsx
- Embeds ttyd terminal in an iframe
- **consoleURL uses window.location.hostname** (not hardcoded IP)
- Pattern: `http://{window.location.hostname}:7681`
- Has 'Open in Tab' button for mobile (iframes block auth popups)

### GuacamoleModal.tsx
- Embeds Guacamole RDP client in an iframe
- Has `rewriteGuacUrl()` helper that replaces localhost with window.location.hostname
- Backend returns URL with localhost:9080 -> frontend rewrites for cross-device access
- Also has 'Open in Tab' for mobile compatibility

## OS-Conditional Rendering
`VMDetailPage.tsx` passes:
- `showConsole={!isWindows}` - ttyd console for Linux only
- `showRemoteDesktop={isWindows}` - Guacamole RDP for Windows only

## Related
- [[05-console-connectivity]] - Deep dive on console URL logic
- [[06-guacamole-integration]] - Deep dive on Guacamole URL logic
