import * as React from 'react';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

export interface WizardStep {
  id: string;
  title: string;
  description?: string;
  optional?: boolean;
}

interface FormWizardProps {
  steps: WizardStep[];
  currentStep: number;
  onStepChange: (step: number) => void;
  onComplete: () => void;
  onCancel: () => void;
  canGoNext?: boolean;
  canGoPrevious?: boolean;
  isSubmitting?: boolean;
  children: React.ReactNode;
}

export function FormWizard({
  steps,
  currentStep,
  onStepChange,
  onComplete,
  onCancel,
  canGoNext = true,
  canGoPrevious = true,
  isSubmitting = false,
  children,
}: FormWizardProps) {
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  const handleNext = () => {
    if (!isLastStep && canGoNext) {
      onStepChange(currentStep + 1);
    } else if (isLastStep) {
      onComplete();
    }
  };

  const handlePrevious = () => {
    if (!isFirstStep && canGoPrevious) {
      onStepChange(currentStep - 1);
    }
  };

  return (
    <div className="space-y-6">
      <WizardProgress steps={steps} currentStep={currentStep} onStepClick={onStepChange} />
      
      <div className="min-h-[400px]">{children}</div>

      <div className="flex justify-between pt-4 border-t">
        <Button
          type="button"
          variant="outline"
          onClick={isFirstStep ? onCancel : handlePrevious}
          disabled={isSubmitting}
        >
          {isFirstStep ? 'Cancelar' : 'Anterior'}
        </Button>

        <Button
          type="button"
          onClick={handleNext}
          disabled={!canGoNext || isSubmitting}
        >
          {isSubmitting ? 'Guardando...' : isLastStep ? 'Finalizar' : 'Siguiente'}
        </Button>
      </div>
    </div>
  );
}

interface WizardProgressProps {
  steps: WizardStep[];
  currentStep: number;
  onStepClick?: (step: number) => void;
}

function WizardProgress({ steps, currentStep, onStepClick }: WizardProgressProps) {
  return (
    <nav aria-label="Progress">
      <ol className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isClickable = onStepClick && (isCompleted || isCurrent);

          return (
            <li key={step.id} className="flex-1 relative">
              {index !== 0 && (
                <div
                  className={cn(
                    'absolute left-0 top-5 -ml-px h-0.5 w-full',
                    isCompleted ? 'bg-primary' : 'bg-muted'
                  )}
                  aria-hidden="true"
                />
              )}

              <button
                type="button"
                onClick={() => isClickable && onStepClick(index)}
                disabled={!isClickable}
                className={cn(
                  'relative flex flex-col items-center group',
                  isClickable && 'cursor-pointer'
                )}
              >
                <span
                  className={cn(
                    'flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors',
                    isCompleted && 'border-primary bg-primary text-primary-foreground',
                    isCurrent && 'border-primary bg-background text-primary',
                    !isCompleted && !isCurrent && 'border-muted bg-background text-muted-foreground'
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-5 w-5" />
                  ) : (
                    <span className="text-sm font-medium">{index + 1}</span>
                  )}
                </span>

                <span className="mt-2 text-center">
                  <span
                    className={cn(
                      'block text-sm font-medium',
                      isCurrent && 'text-primary',
                      !isCurrent && 'text-muted-foreground'
                    )}
                  >
                    {step.title}
                    {step.optional && (
                      <span className="ml-1 text-xs text-muted-foreground">(opcional)</span>
                    )}
                  </span>
                  {step.description && (
                    <span className="block text-xs text-muted-foreground mt-1">
                      {step.description}
                    </span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
