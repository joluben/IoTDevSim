import * as React from 'react';
import { ChevronDown, ChevronRight, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface FormSectionProps {
  title: string;
  description?: string;
  helpText?: string;
  defaultOpen?: boolean;
  collapsible?: boolean;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function FormSection({
  title,
  description,
  helpText,
  defaultOpen = true,
  collapsible = true,
  required = false,
  children,
  className,
}: FormSectionProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);

  if (!collapsible) {
    return (
      <div className={cn('space-y-4', className)}>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold">
              {title}
              {required && <span className="text-destructive ml-1">*</span>}
            </h3>
            {helpText && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-5 w-5">
                      <Info className="h-4 w-4 text-muted-foreground" />
                      <span className="sr-only">Ayuda</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    <p className="text-sm">{helpText}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        <div className="space-y-4">{children}</div>
      </div>
    );
  }

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className={cn('space-y-2', className)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-1">
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="p-0 h-auto">
              {isOpen ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <span className="sr-only">Toggle</span>
            </Button>
          </CollapsibleTrigger>
          <div className="space-y-1 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold">
                {title}
                {required && <span className="text-destructive ml-1">*</span>}
              </h3>
              {helpText && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-5 w-5">
                        <Info className="h-4 w-4 text-muted-foreground" />
                        <span className="sr-only">Ayuda</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="text-sm">{helpText}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
          </div>
        </div>
      </div>
      <CollapsibleContent className="space-y-4 pt-2">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}
