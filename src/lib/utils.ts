// Utility functions will go here
export function cn(...classes: (string | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}
