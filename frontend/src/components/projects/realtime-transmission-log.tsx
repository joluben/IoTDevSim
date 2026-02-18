import { useRef, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { TransmissionHistoryEntry } from '@/types/project';

interface RealtimeTransmissionLogProps {
  entries: TransmissionHistoryEntry[];
  isLoading?: boolean;
  maxEntries?: number;
}

export function RealtimeTransmissionLog({
  entries,
  isLoading,
  maxEntries = 100,
}: RealtimeTransmissionLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries]);

  const displayEntries = entries.slice(-maxEntries);

  return (
    <Card className="h-[500px] flex flex-col overflow-hidden">
      <CardHeader className="pb-3 py-3 shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Real-time Transmission Log</CardTitle>
          <Badge variant="outline" className="text-xs">
            {entries.length} entries
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 min-h-0 overflow-hidden">
        <ScrollArea className="h-full w-full" ref={scrollRef}>
          <div className="px-4 py-2 space-y-1 min-w-0 overflow-hidden">
            {isLoading && entries.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                Loading history...
              </p>
            ) : entries.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No transmission activity yet. Start transmission to see logs.
              </p>
            ) : (
              displayEntries.map((entry, index) => (
                <LogEntryItem key={entry.id} entry={entry} isLatest={index === displayEntries.length - 1} />
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

interface LogEntryItemProps {
  entry: TransmissionHistoryEntry;
  isLatest?: boolean;
}

function LogEntryItem({ entry, isLatest }: LogEntryItemProps) {
  const timestamp = new Date(entry.timestamp).toLocaleTimeString();
  
  const statusColors: Record<string, string> = {
    success: 'text-green-600 bg-green-500/10',
    failed: 'text-red-600 bg-red-500/10',
    error: 'text-red-600 bg-red-500/10',
  };

  return (
    <div 
      className={`flex items-center gap-3 text-xs py-1.5 px-2 rounded min-w-0 ${
        isLatest ? 'bg-muted/50' : ''
      }`}
    >
      <span className="text-muted-foreground font-mono whitespace-nowrap">
        {timestamp}
      </span>
      
      <Badge 
        variant="secondary" 
        className={`text-[10px] px-1.5 py-0 h-4 ${statusColors[entry.status]}`}
      >
        {entry.status}
      </Badge>
      
      <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 uppercase">
        {entry.protocol}
      </Badge>
      
      <span className="font-medium truncate max-w-[250px]">
        {entry.device_name || 'Unknown'}
      </span>
      
      {entry.topic && (
        <span className="text-muted-foreground truncate max-w-[150px] hidden sm:inline">
          → {entry.topic}
        </span>
      )}
      
      <span className="text-muted-foreground ml-auto whitespace-nowrap">
        {entry.payload_size} B
        {entry.latency_ms != null && ` • ${entry.latency_ms}ms`}
      </span>
    </div>
  );
}
