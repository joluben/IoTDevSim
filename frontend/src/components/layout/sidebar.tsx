import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Settings,
  ChevronRight
} from 'lucide-react';
import { useUIStore } from '@/app/store';
import { useI18n } from '@/contexts/i18n-context';
import { navigationGroups, filterNavigationItems } from '@/app/config/navigation';
import { useAuthStore } from '@/app/store';

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const location = useLocation();
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const { t } = useI18n();
  const { user } = useAuthStore();

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  // Build filtered items from navigation groups
  const items = React.useMemo(() => {
    const groups = navigationGroups.map((group) => (
      filterNavigationItems(group.items, user?.permissions ?? [], user?.role ?? 'viewer')
    ));
    // Flatten groups for simple render (parent and its children)
    return groups.flat().flatMap((it) => it.children ? [it, ...it.children] : [it]);
  }, [user]);

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 md:hidden" 
          onClick={closeSidebar}
        />
      )}
      
      {/* Sidebar */}
      <div className={cn(
        "fixed left-0 top-0 z-50 h-full w-64 transform border-r bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 transition-transform duration-300 ease-in-out md:relative md:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full",
        className
      )}>
        <div className="flex h-full flex-col">
          {/* Navigation */}
          <ScrollArea className="flex-1 px-4 py-6">
            <nav className="space-y-2">
              {items.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href;
                return (
                  <Link key={item.id} to={item.href} onClick={closeSidebar}>
                    <Button
                      variant={isActive ? 'secondary' : 'ghost'}
                      className={cn('w-full justify-start', isActive && 'bg-secondary')}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      <Icon className="mr-2 h-4 w-4" />
                      <span>{item.label}</span>
                      {item.badge != null && (
                        <span className="ml-auto inline-flex items-center justify-center rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                          {item.badge}
                        </span>
                      )}
                      {isActive && <ChevronRight className="ml-2 h-4 w-4" />}
                    </Button>
                  </Link>
                );
              })}
            </nav>
          </ScrollArea>

          <Separator />

          {/* Settings */}
          <div className="p-4">
            <Link to="/settings" onClick={closeSidebar}>
              <Button
                variant={location.pathname === '/settings' ? "secondary" : "ghost"}
                className="w-full justify-start"
              >
                <Settings className="mr-2 h-4 w-4" />
                {t.nav.settings}
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
