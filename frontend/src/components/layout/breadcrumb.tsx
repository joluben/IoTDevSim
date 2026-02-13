import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { ChevronRight, Home } from 'lucide-react';
import { useUIStore } from '@/app/store';
import { getActiveNavigationItem, findNavigationItemByHref } from '@/app/config/navigation';
import { ROUTES } from '@/app/config/constants';

interface BreadcrumbItem {
  label: string;
  href?: string;
  isActive?: boolean;
}

interface BreadcrumbProps {
  className?: string;
  items?: BreadcrumbItem[];
  showHome?: boolean;
  maxItems?: number;
}

// Generate breadcrumb items from current route
function generateBreadcrumbsFromRoute(pathname: string): BreadcrumbItem[] {
  const segments = pathname.split('/').filter(Boolean);
  const breadcrumbs: BreadcrumbItem[] = [];

  // Build breadcrumbs from path segments
  let currentPath = '';
  for (let i = 0; i < segments.length; i++) {
    currentPath += `/${segments[i]}`;
    const isLast = i === segments.length - 1;
    
    // Try to find navigation item for this path
    const navItem = findNavigationItemByHref(currentPath);
    
    if (navItem) {
      breadcrumbs.push({
        label: navItem.label,
        href: isLast ? undefined : currentPath,
        isActive: isLast,
      });
    } else {
      // Fallback to segment name with basic formatting
      const label = segments[i]
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
      
      breadcrumbs.push({
        label,
        href: isLast ? undefined : currentPath,
        isActive: isLast,
      });
    }
  }

  return breadcrumbs;
}

// Get route-specific breadcrumbs with custom logic
function getCustomBreadcrumbs(pathname: string): BreadcrumbItem[] | null {
  // Handle specific route patterns
  if (pathname.startsWith('/connections/')) {
    const id = pathname.split('/')[2];
    if (id && id !== 'new') {
      return [
        { label: 'Connections', href: ROUTES.connections },
        { label: `Connection ${id}`, isActive: true },
      ];
    }
  }
  
  if (pathname.startsWith('/devices/')) {
    const id = pathname.split('/')[2];
    if (id && id !== 'new') {
      return [
        { label: 'Devices', href: ROUTES.devices },
        { label: `Device ${id}`, isActive: true },
      ];
    }
  }
  
  if (pathname.startsWith('/projects/')) {
    const id = pathname.split('/')[2];
    if (id && id !== 'new') {
      return [
        { label: 'Projects', href: ROUTES.projects },
        { label: `Project ${id}`, isActive: true },
      ];
    }
  }

  // Handle settings sub-pages
  if (pathname.startsWith('/settings/')) {
    const subPage = pathname.split('/')[2];
    const subPageLabels: Record<string, string> = {
      general: 'General',
      security: 'Security',
      notifications: 'Notifications',
      integrations: 'Integrations',
      billing: 'Billing',
    };
    
    return [
      { label: 'Settings', href: ROUTES.settings },
      { label: subPageLabels[subPage] || subPage, isActive: true },
    ];
  }

  return null;
}

export function Breadcrumb({ 
  className, 
  items: customItems, 
  showHome = true, 
  maxItems = 5 
}: BreadcrumbProps) {
  const location = useLocation();
  const { breadcrumbs: storeBreadcrumbs } = useUIStore();

  // Determine which breadcrumbs to use
  const breadcrumbItems = React.useMemo(() => {
    // Use custom items if provided
    if (customItems) {
      return customItems;
    }

    // Use store breadcrumbs if available
    if (storeBreadcrumbs.length > 0) {
      return storeBreadcrumbs.map((item: { label: string; href?: string }, index: number, array: typeof storeBreadcrumbs) => ({
        label: item.label,
        href: index === array.length - 1 ? undefined : item.href,
        isActive: index === array.length - 1,
      }));
    }

    // Try custom route logic
    const customBreadcrumbs = getCustomBreadcrumbs(location.pathname);
    if (customBreadcrumbs) {
      return customBreadcrumbs;
    }

    // Fallback to auto-generated breadcrumbs
    return generateBreadcrumbsFromRoute(location.pathname);
  }, [customItems, storeBreadcrumbs, location.pathname]);

  // Add home breadcrumb if requested and not already present
  const finalBreadcrumbs = React.useMemo(() => {
    const items = [...breadcrumbItems];
    
    if (showHome && location.pathname !== ROUTES.dashboard) {
      // Check if home is already the first item
      const hasHome = items[0]?.href === ROUTES.dashboard;
      if (!hasHome) {
        items.unshift({
          label: 'Dashboard',
          href: ROUTES.dashboard,
        });
      }
    }

    // Truncate if too many items
    if (items.length > maxItems) {
      const start = items.slice(0, 1); // Keep first item (usually home)
      const end = items.slice(-(maxItems - 2)); // Keep last items
      return [
        ...start,
        { label: '...', isActive: false }, // Ellipsis indicator
        ...end,
      ];
    }

    return items;
  }, [breadcrumbItems, showHome, location.pathname, maxItems]);

  // Don't render if no breadcrumbs or only one item
  if (finalBreadcrumbs.length <= 1) {
    return null;
  }

  return (
    <nav 
      className={cn("flex items-center space-x-1 text-sm text-muted-foreground", className)}
      aria-label="Breadcrumb"
    >
      <ol className="flex items-center space-x-1">
        {finalBreadcrumbs.map((item, index) => (
          <li key={index} className="flex items-center">
            {index > 0 && (
              <ChevronRight className="h-4 w-4 mx-1" aria-hidden="true" />
            )}
            
            {item.href ? (
              <Link
                to={item.href}
                className="hover:text-foreground transition-colors font-medium"
                aria-current={item.isActive ? 'page' : undefined}
              >
                {index === 0 && showHome && item.label === 'Dashboard' ? (
                  <Home className="h-4 w-4" aria-label="Dashboard" />
                ) : (
                  item.label
                )}
              </Link>
            ) : (
              <span 
                className={cn(
                  "font-medium",
                  item.isActive ? "text-foreground" : "text-muted-foreground"
                )}
                aria-current={item.isActive ? 'page' : undefined}
              >
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

// Hook to update breadcrumbs programmatically
export function useBreadcrumbs() {
  const { setBreadcrumbs } = useUIStore();

  const updateBreadcrumbs = React.useCallback((breadcrumbs: Array<{ label: string; href?: string }>) => {
    setBreadcrumbs(breadcrumbs);
  }, [setBreadcrumbs]);

  const clearBreadcrumbs = React.useCallback(() => {
    setBreadcrumbs([]);
  }, [setBreadcrumbs]);

  return {
    updateBreadcrumbs,
    clearBreadcrumbs,
  };
}

// Component for setting breadcrumbs declaratively
interface BreadcrumbSetterProps {
  items: Array<{ label: string; href?: string }>;
}

export function BreadcrumbSetter({ items }: BreadcrumbSetterProps) {
  const { updateBreadcrumbs } = useBreadcrumbs();

  React.useEffect(() => {
    updateBreadcrumbs(items);
    
    // Cleanup on unmount
    return () => {
      updateBreadcrumbs([]);
    };
  }, [items, updateBreadcrumbs]);

  return null;
}
