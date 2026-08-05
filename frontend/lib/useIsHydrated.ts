import { useSyncExternalStore } from "react";

const subscribeToNothing = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

/**
 * Report whether React has finished hydrating this component on the client.
 *
 * Returns false during server rendering and throughout the hydration render,
 * then true once hydration completes. Use it to hold back interactions that
 * depend on event handlers being attached: before hydration a submit falls
 * through to the browser's native form submission, which on a credential form
 * puts the password in the URL.
 */
export function useIsHydrated(): boolean {
  return useSyncExternalStore(
    subscribeToNothing,
    getClientSnapshot,
    getServerSnapshot,
  );
}
