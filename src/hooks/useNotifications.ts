import { useState, useCallback, useRef } from 'react';
import { useToast } from '@/components/ui/use-toast';

type NotificationType = 'success' | 'error' | 'warning' | 'info';

interface Notification {
  id: string;
  message: string;
  type: NotificationType;
  duration?: number;
}

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const { toast } = useToast();
  const lastErrorTime = useRef(0);
  const ERROR_COOLDOWN = 5 * 60 * 1000; // 5 minutes

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const showNotification = useCallback((
    message: string, 
    type: NotificationType = 'info',
    duration: number = 5000
  ) => {
    // Skip duplicate error notifications within cooldown period
    if (type === 'error') {
      const now = Date.now();
      if (now - lastErrorTime.current < ERROR_COOLDOWN) {
        return;
      }
      lastErrorTime.current = now;
    }

    const id = Math.random().toString(36).substr(2, 9);
    const notification = { id, message, type, duration };

    setNotifications(prev => [...prev, notification]);

    // Auto-dismiss notification after duration
    if (duration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, duration);
    }

    // Show toast notification
    toast({
      title: type.charAt(0).toUpperCase() + type.slice(1),
      description: message,
      variant: type === 'error' ? 'destructive' : 'default',
      duration,
    });

    return id;
  }, [toast, removeNotification, ERROR_COOLDOWN]);

  return {
    notifications,
    showNotification,
    removeNotification,
  };
}
