import { useEffect, useRef, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

type MessageHandler = (data: DeviceWSMessage) => void;

export interface DeviceWSMessage {
  type: 'device_update' | 'transmission_log' | 'subscribed' | 'unsubscribed' | 'subscribed_all' | 'unsubscribed_all' | 'pong' | 'error';
  device_id?: string;
  data?: Record<string, unknown>;
  message?: string;
}

interface UseDeviceWebSocketOptions {
  autoConnect?: boolean;
  subscribeAll?: boolean;
  deviceIds?: string[];
  onMessage?: MessageHandler;
}

export function useDeviceWebSocket(options: UseDeviceWebSocketOptions = {}) {
  const {
    autoConnect = true,
    subscribeAll = false,
    deviceIds = [],
    onMessage,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const getWsUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = import.meta.env.VITE_API_PORT || '8000';
    return `${protocol}//${host}:${port}/api/v1/ws/devices`;
  }, []);

  const send = useCallback((payload: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  const subscribeDevice = useCallback(
    (deviceId: string) => send({ action: 'subscribe_device', device_id: deviceId }),
    [send]
  );

  const unsubscribeDevice = useCallback(
    (deviceId: string) => send({ action: 'unsubscribe_device', device_id: deviceId }),
    [send]
  );

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(getWsUrl());

    ws.onopen = () => {
      setConnected(true);

      if (subscribeAll) {
        send({ action: 'subscribe_all' });
      }
      deviceIds.forEach((id) => subscribeDevice(id));
    };

    ws.onmessage = (event) => {
      try {
        const msg: DeviceWSMessage = JSON.parse(event.data);

        // Invalidate device queries on updates
        if (msg.type === 'device_update' || msg.type === 'transmission_log') {
          queryClient.invalidateQueries({ queryKey: ['devices'] });
        }

        onMessage?.(msg);
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setConnected(false);
      // Auto-reconnect after 3 seconds
      reconnectTimer.current = setTimeout(() => {
        if (autoConnect) connect();
      }, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [getWsUrl, subscribeAll, deviceIds, subscribeDevice, send, onMessage, queryClient, autoConnect]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current);
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  useEffect(() => {
    if (autoConnect) connect();
    return () => disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]);

  return {
    connected,
    connect,
    disconnect,
    send,
    subscribeDevice,
    unsubscribeDevice,
  };
}
