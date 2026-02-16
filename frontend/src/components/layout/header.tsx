import React from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Switch } from '@/components/ui/switch';
import { 
  Menu,
  Sun,
  Moon,
  Globe,
  User,
  Settings,
  LogOut
} from 'lucide-react';
import { useUIStore } from '@/app/store';
import { useAuthStore } from '@/app/store';
import { useTheme } from '@/app/providers/theme-provider';
import { useI18n } from '@/contexts/i18n-context';
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { quickAccessItems, navigationGroups, filterNavigationItems, type NavigationItem } from '@/app/config/navigation';
import { useNavigate, Link } from 'react-router-dom';

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const { user, logout } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const { language, setLanguage, t } = useI18n();
  const navigate = useNavigate();

  // Command palette state
  const [cmdOpen, setCmdOpen] = React.useState(false);

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key.toLowerCase() === 'k') && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        setCmdOpen((o) => !o);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  const toggleLanguage = () => {
    setLanguage(language === 'es' ? 'en' : 'es');
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <header className={cn(
      "border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60",
      className
    )}>
      <div className="flex h-16 items-center px-6">
        {/* Mobile sidebar toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden mr-2"
          onClick={toggleSidebar}
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* Logo */}
        <div className="flex items-center space-x-2">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">IoT</span>
          </div>
          <span className="font-semibold text-lg hidden sm:block">DevSim</span>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Controls */}
        <div className="flex items-center space-x-4">
          {/* Command Palette Shortcut */}
          <Button
            variant="ghost"
            size="sm"
            className="hidden md:inline-flex text-xs text-muted-foreground border rounded px-2 py-1"
            onClick={() => setCmdOpen(true)}
            aria-label="Open command palette"
          >
            <kbd className="mr-1">Ctrl</kbd>+
            <kbd className="ml-1">K</kbd>
          </Button>

          {/* Language Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleLanguage}
            className="h-9 w-9"
          >
            <Globe className="h-4 w-4" />
            <span className="sr-only">Toggle language</span>
          </Button>
          <span className="text-sm text-muted-foreground hidden sm:block">
            {language.toUpperCase()}
          </span>

          {/* Theme Toggle */}
          <div className="flex items-center space-x-2">
            <Sun className="h-4 w-4" />
            <Switch
              checked={theme === 'dark'}
              onCheckedChange={toggleTheme}
            />
            <Moon className="h-4 w-4" />
          </div>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={user?.avatar} alt={user?.name || 'User'} />
                  <AvatarFallback>
                    {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {user?.name || 'Usuario'}
                  </p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {user?.email || 'usuario@ejemplo.com'}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate('/profile')}>
                <User className="mr-2 h-4 w-4" />
                <span>{t.common.profile}</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/settings')}>
                <Settings className="mr-2 h-4 w-4" />
                <span>{t.nav.settings}</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout}>
                <LogOut className="mr-2 h-4 w-4" />
                <span>{t.common.logout}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Command Palette */}
      <CommandDialog open={cmdOpen} onOpenChange={setCmdOpen}>
        <CommandInput placeholder="Search navigation..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          {/* Quick Access */}
          <CommandGroup heading="Quick Access">
            {quickAccessItems.map((item) => (
              <CommandItem
                key={item.id}
                value={`${item.label} ${item.description ?? ''}`}
                onSelect={() => {
                  setCmdOpen(false);
                  navigate(item.href);
                }}
              >
                <item.icon className="mr-2 h-4 w-4" />
                <span>{item.label}</span>
              </CommandItem>
            ))}
          </CommandGroup>
          {/* Navigation Groups filtered by permissions/role */}
          {navigationGroups.map((group) => {
            const filtered = filterNavigationItems(
              group.items,
              user?.permissions ?? [],
              user?.roles ?? ['viewer']
            );

            const flat: NavigationItem[] = filtered.flatMap((it) =>
              it.children ? [it, ...it.children] : [it]
            );

            if (flat.length === 0) return null;
            return (
              <CommandGroup key={group.id} heading={group.label}>
                {flat.map((item) => (
                  <CommandItem
                    key={item.id}
                    value={`${item.label} ${item.description ?? ''}`}
                    onSelect={() => {
                      setCmdOpen(false);
                      navigate(item.href);
                    }}
                  >
                    <item.icon className="mr-2 h-4 w-4" />
                    <span>{item.label}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            );
          })}
        </CommandList>
      </CommandDialog>
    </header>
  );
}
