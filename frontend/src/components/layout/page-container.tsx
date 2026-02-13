import React from 'react';
import { cn } from '@/lib/utils';
import { Breadcrumb } from './breadcrumb';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface PageAction {
  label: string;
  onClick: () => void;
  variant?: 'default' | 'outline' | 'secondary' | 'ghost' | 'destructive';
  icon?: React.ComponentType<{ className?: string }>;
  disabled?: boolean;
  loading?: boolean;
}

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
  
  // Header props
  title?: string;
  description?: string;
  showBreadcrumb?: boolean;
  showBackButton?: boolean;
  backButtonHref?: string;
  
  // Actions
  actions?: PageAction[];
  primaryAction?: PageAction;
  
  // Layout options
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  spacing?: 'none' | 'sm' | 'md' | 'lg';
  
  // Content organization
  header?: React.ReactNode;
  sidebar?: React.ReactNode;
  footer?: React.ReactNode;
}

const maxWidthClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-4xl',
  xl: 'max-w-6xl',
  '2xl': 'max-w-7xl',
  full: 'max-w-none',
};

const paddingClasses = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

const spacingClasses = {
  none: 'space-y-0',
  sm: 'space-y-4',
  md: 'space-y-6',
  lg: 'space-y-8',
};

export function PageContainer({
  children,
  className,
  title,
  description,
  showBreadcrumb = true,
  showBackButton = false,
  backButtonHref,
  actions = [],
  primaryAction,
  maxWidth = 'full',
  padding = 'md',
  spacing = 'md',
  header,
  sidebar,
  footer,
}: PageContainerProps) {
  const navigate = useNavigate();

  const handleBackClick = () => {
    if (backButtonHref) {
      navigate(backButtonHref);
    } else {
      navigate(-1);
    }
  };

  const hasPageHeader = title || description || showBreadcrumb || showBackButton || actions.length > 0 || primaryAction;

  return (
    <div className={cn("min-h-full", className)}>
      <div className={cn(
        "mx-auto",
        maxWidthClasses[maxWidth],
        paddingClasses[padding]
      )}>
        <div className={cn(spacingClasses[spacing])}>
          {/* Breadcrumb */}
          {showBreadcrumb && (
            <div className="mb-4">
              <Breadcrumb />
            </div>
          )}

          {/* Custom header */}
          {header && (
            <div className="mb-6">
              {header}
            </div>
          )}

          {/* Page header */}
          {hasPageHeader && (
            <div className="flex flex-col gap-4 mb-8">
              {/* Back button */}
              {showBackButton && (
                <div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleBackClick}
                    className="flex items-center gap-2 text-muted-foreground hover:text-foreground"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back
                  </Button>
                </div>
              )}

              {/* Title and actions */}
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="space-y-1">
                  {title && (
                    <h1 className="text-3xl font-bold tracking-tight">
                      {title}
                    </h1>
                  )}
                  {description && (
                    <p className="text-muted-foreground">
                      {description}
                    </p>
                  )}
                </div>

                {/* Actions */}
                {(actions.length > 0 || primaryAction) && (
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                    {/* Secondary actions */}
                    {actions.map((action, index) => {
                      const IconComponent = action.icon;
                      return (
                        <Button
                          key={index}
                          variant={action.variant || 'outline'}
                          onClick={action.onClick}
                          disabled={action.disabled || action.loading}
                          className="flex items-center gap-2"
                        >
                          {action.loading ? (
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                          ) : (
                            IconComponent && <IconComponent className="h-4 w-4" />
                          )}
                          {action.label}
                        </Button>
                      );
                    })}

                    {/* Primary action */}
                    {primaryAction && (
                      <Button
                        variant={primaryAction.variant || 'default'}
                        onClick={primaryAction.onClick}
                        disabled={primaryAction.disabled || primaryAction.loading}
                        className="flex items-center gap-2"
                      >
                        {primaryAction.loading ? (
                          <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                        ) : (
                          primaryAction.icon && <primaryAction.icon className="h-4 w-4" />
                        )}
                        {primaryAction.label}
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Main content area */}
          {sidebar ? (
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
              {/* Sidebar */}
              <div className="lg:col-span-1">
                <div className="sticky top-8">
                  {sidebar}
                </div>
              </div>

              {/* Main content */}
              <div className="lg:col-span-3">
                {children}
              </div>
            </div>
          ) : (
            <div>
              {children}
            </div>
          )}

          {/* Footer */}
          {footer && (
            <div className="mt-8 pt-8 border-t">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Specialized page containers for common layouts

interface DashboardPageProps extends Omit<PageContainerProps, 'maxWidth' | 'padding'> {
  widgets?: React.ReactNode;
}

export function DashboardPage({ widgets, children, ...props }: DashboardPageProps) {
  return (
    <PageContainer maxWidth="full" padding="md" {...props}>
      {widgets && (
        <div className="mb-8">
          {widgets}
        </div>
      )}
      {children}
    </PageContainer>
  );
}

interface FormPageProps extends Omit<PageContainerProps, 'maxWidth'> {
  formWidth?: 'sm' | 'md' | 'lg';
}

export function FormPage({ formWidth = 'md', children, ...props }: FormPageProps) {
  return (
    <PageContainer maxWidth={formWidth} {...props}>
      {children}
    </PageContainer>
  );
}

interface DetailPageProps extends PageContainerProps {
  tabs?: Array<{
    id: string;
    label: string;
    content: React.ReactNode;
    badge?: string | number;
  }>;
  activeTab?: string;
  onTabChange?: (tabId: string) => void;
}

export function DetailPage({ 
  tabs, 
  activeTab, 
  onTabChange, 
  children, 
  ...props 
}: DetailPageProps) {
  const [currentTab, setCurrentTab] = React.useState(activeTab || tabs?.[0]?.id || '');

  const handleTabChange = (tabId: string) => {
    setCurrentTab(tabId);
    onTabChange?.(tabId);
  };

  return (
    <PageContainer {...props}>
      {tabs && tabs.length > 0 ? (
        <div className="space-y-6">
          {/* Tab navigation */}
          <div className="border-b">
            <nav className="flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={cn(
                    "flex items-center gap-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors",
                    currentTab === tab.id
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground"
                  )}
                >
                  {tab.label}
                  {tab.badge && (
                    <span className="ml-2 bg-muted text-muted-foreground rounded-full px-2 py-0.5 text-xs">
                      {tab.badge}
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab content */}
          <div>
            {tabs.find(tab => tab.id === currentTab)?.content || children}
          </div>
        </div>
      ) : (
        children
      )}
    </PageContainer>
  );
}
