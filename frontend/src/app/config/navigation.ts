/**
 * Navigation Configuration
 * Defines the navigation structure for the application
 */

import {
  LayoutDashboard,
  Cable,
  Cpu,
  FolderKanban,
  BarChart3,
  Settings,
  User,
  Home,
  Activity,
  Database,
  Zap,
  type LucideIcon
} from 'lucide-react';
import { ROUTES } from './constants';

export interface NavigationItem {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  description?: string;
  badge?: string | number;
  children?: NavigationItem[];
  requiredPermission?: string;
  requiredRole?: 'admin' | 'user' | 'viewer';
  isExternal?: boolean;
  isNew?: boolean;
  isBeta?: boolean;
}

export interface NavigationGroup {
  id: string;
  label: string;
  items: NavigationItem[];
  requiredPermission?: string;
  requiredRole?: 'admin' | 'user' | 'viewer';
}

// Main navigation items
export const navigationItems: NavigationItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    href: ROUTES.dashboard,
    icon: LayoutDashboard,
    description: 'Overview and analytics',
  },
  {
    id: 'connections',
    label: 'Connections',
    href: ROUTES.connections,
    icon: Cable,
    description: 'Manage IoT connections',
  },
  {
    id: 'datasets',
    label: 'Datasets',
    href: ROUTES.datasets,
    icon: Database,
    description: 'Manage data sources for simulation',
  },
  {
    id: 'devices',
    label: 'Devices',
    href: ROUTES.devices,
    icon: Cpu,
    description: 'Configure and monitor devices',
  },
  {
    id: 'projects',
    label: 'Projects',
    href: ROUTES.projects,
    icon: FolderKanban,
    description: 'Organize devices into projects',
  },
  {
    id: 'analytics',
    label: 'Analytics',
    href: ROUTES.analytics,
    icon: BarChart3,
    description: 'View insights and reports',
    requiredPermission: 'analytics:view',
  },
];

// Secondary navigation items
export const secondaryNavigationItems: NavigationItem[] = [
  {
    id: 'profile',
    label: 'Profile',
    href: ROUTES.profile,
    icon: User,
    description: 'Manage your profile',
  },
  {
    id: 'settings',
    label: 'Settings',
    href: ROUTES.settings,
    icon: Settings,
    description: 'Application settings',
    requiredRole: 'admin',
  },
  {
    id: 'users-management',
    label: 'User Management',
    href: ROUTES.usersManagement,
    icon: User,
    description: 'Manage users, groups and permissions',
    requiredRole: 'admin',
    requiredPermission: 'users:read',
  },
];

// Grouped navigation structure
export const navigationGroups: NavigationGroup[] = [
  {
    id: 'main',
    label: 'Main',
    items: navigationItems,
  },
];

// Quick access items for header
export const quickAccessItems: NavigationItem[] = [
  {
    id: 'home',
    label: 'Home',
    href: ROUTES.dashboard,
    icon: Home,
    description: 'Go to dashboard',
  },
  {
    id: 'new-device',
    label: 'New Device',
    href: `${ROUTES.devices}?action=create`,
    icon: Cpu,
    description: 'Create a new device',
  },
  {
    id: 'new-connection',
    label: 'New Connection',
    href: `${ROUTES.connections}?action=create`,
    icon: Cable,
    description: 'Create a new connection',
  },
  {
    id: 'new-project',
    label: 'New Project',
    href: ROUTES.projectNew,
    icon: FolderKanban,
    description: 'Create a new project',
  },
];

// Utility functions
export const findNavigationItem = (id: string): NavigationItem | undefined => {
  const allItems = [
    ...navigationItems,
    ...secondaryNavigationItems,
    ...navigationGroups.flatMap(group => group.items.flatMap(item =>
      item.children ? [item, ...item.children] : [item]
    )),
  ];

  return allItems.find(item => item.id === id);
};

export const findNavigationItemByHref = (href: string): NavigationItem | undefined => {
  const allItems = [
    ...navigationItems,
    ...secondaryNavigationItems,
    ...navigationGroups.flatMap(group => group.items.flatMap(item =>
      item.children ? [item, ...item.children] : [item]
    )),
  ];

  return allItems.find(item => item.href === href);
};

export const getActiveNavigationItem = (pathname: string): NavigationItem | undefined => {
  const allItems = [
    ...navigationItems,
    ...secondaryNavigationItems,
    ...navigationGroups.flatMap(group => group.items.flatMap(item =>
      item.children ? [item, ...item.children] : [item]
    )),
  ];

  // Find exact match first
  let activeItem = allItems.find(item => item.href === pathname);

  // If no exact match, find the best partial match
  if (!activeItem) {
    const pathSegments = pathname.split('/').filter(Boolean);
    activeItem = allItems.find(item => {
      const itemSegments = item.href.split('/').filter(Boolean);
      return itemSegments.length > 0 &&
        pathSegments.length >= itemSegments.length &&
        itemSegments.every((segment, index) => segment === pathSegments[index]);
    });
  }

  return activeItem;
};

// Check if user has permission to access navigation item
export const hasNavigationPermission = (
  item: NavigationItem,
  userPermissions: string[] = [],
  userRoles: string[] = ['viewer']
): boolean => {
  // Check role requirement
  if (item.requiredRole && !userRoles.includes(item.requiredRole)) {
    return false;
  }

  // Check permission requirement
  if (item.requiredPermission && !userPermissions.includes(item.requiredPermission)) {
    return false;
  }

  return true;
};

// Filter navigation items based on user permissions
export const filterNavigationItems = (
  items: NavigationItem[],
  userPermissions: string[] = [],
  userRoles: string[] = ['viewer']
): NavigationItem[] => {
  return items.filter(item => hasNavigationPermission(item, userPermissions, userRoles))
    .map(item => ({
      ...item,
      children: item.children
        ? filterNavigationItems(item.children, userPermissions, userRoles)
        : undefined,
    }));
};
