import * as React from 'react';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { MoreHorizontal, Plus, ChevronLeft, ChevronRight, KeyRound } from 'lucide-react';
import { ConfirmDialog } from '@/components/shared/confirm-dialog';

import { PageContainer } from '@/components/layout/page-container';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { useUIStore } from '@/app/store';
import {
  useCreateUser,
  useDeleteUser,
  useResetUserPassword,
  useRestoreUser,
  useToggleUserStatus,
  useUpdateUser,
  useUsersList,
} from '@/hooks/useUsers';
import type {
  ManagedPermission,
  ManagedUserFilters,
  ManagedUserListItem,
  UserGroup,
} from '@/types/user-management';
import type { UseFormReturn } from 'react-hook-form';

const PERMISSION_RESOURCES = ['connections', 'datasets', 'devices', 'projects'] as const;

const createSchema = z.object({
  email: z.string().email('Invalid email'),
  full_name: z.string().min(2, 'Name must have at least 2 characters'),
  group: z.enum(['admin', 'user']),
  permissions: z.array(z.string()),
});

const updateSchema = z.object({
  full_name: z.string().min(2, 'Name must have at least 2 characters'),
  group: z.enum(['admin', 'user']),
  permissions: z.array(z.string()),
});

type CreateFormValues = z.infer<typeof createSchema>;
type UpdateFormValues = z.infer<typeof updateSchema>;
type ManagedUserApiError = Error & { status?: number; code?: string; details?: unknown };

const DEFAULT_FILTERS: ManagedUserFilters = {
  search: undefined,
  group: undefined,
  is_active: undefined,
  skip: 0,
  limit: 20,
  sort_by: 'created_at',
  sort_order: 'desc',
};

function hasPermission(permissions: string[], resource: string, level: 'read' | 'write'): boolean {
  return permissions.includes(`${resource}:${level}`);
}

function permissionSummaryBadge(user: ManagedUserListItem, resource: string): React.ReactNode {
  const hasWrite = hasPermission(user.permissions, resource, 'write');
  const hasRead = hasPermission(user.permissions, resource, 'read');

  if (hasWrite) {
    return <Badge variant="default">Write</Badge>;
  }

  if (hasRead) {
    return <Badge variant="secondary">Read</Badge>;
  }

  return <Badge variant="outline">None</Badge>;
}

function buildUserPermissionsFromMatrix(resourceWriteFlags: Record<string, boolean>): ManagedPermission[] {
  const permissions: ManagedPermission[] = [];

  PERMISSION_RESOURCES.forEach((resource) => {
    if (resourceWriteFlags[resource]) {
      permissions.push(`${resource}:write` as ManagedPermission);
    } else {
      permissions.push(`${resource}:read` as ManagedPermission);
    }
  });

  return permissions;
}

export default function UsersManagementPage() {
  const addNotification = useUIStore((state) => state.addNotification);

  const [filters, setFilters] = React.useState<ManagedUserFilters>(DEFAULT_FILTERS);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editingUser, setEditingUser] = React.useState<ManagedUserListItem | null>(null);
  const [deletingUser, setDeletingUser] = React.useState<ManagedUserListItem | null>(null);
  const [togglingUser, setTogglingUser] = React.useState<ManagedUserListItem | null>(null);
  const [restoreCandidate, setRestoreCandidate] = React.useState<CreateFormValues | null>(null);
  const [resetPasswordUser, setResetPasswordUser] = React.useState<ManagedUserListItem | null>(null);

  const usersQuery = useUsersList(filters);
  const createMutation = useCreateUser();
  const restoreMutation = useRestoreUser();
  const updateMutation = useUpdateUser();
  const toggleMutation = useToggleUserStatus();
  const deleteMutation = useDeleteUser();
  const resetPasswordMutation = useResetUserPassword();

  const createForm = useForm<CreateFormValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      email: '',
      full_name: '',
      group: 'user',
      permissions: ['connections:read', 'datasets:read', 'devices:read', 'projects:read'],
    },
  });

  const updateForm = useForm<UpdateFormValues>({
    resolver: zodResolver(updateSchema),
    defaultValues: {
      full_name: '',
      group: 'user',
      permissions: ['connections:read', 'datasets:read', 'devices:read', 'projects:read'],
    },
  });

  const users = usersQuery.data?.items ?? [];

  React.useEffect(() => {
    if (!usersQuery.isError) return;

    addNotification({
      type: 'error',
      title: 'Failed to load users',
      message: usersQuery.error instanceof Error ? usersQuery.error.message : 'Unexpected error',
    });
  }, [usersQuery.isError, usersQuery.error, addNotification]);

  const handleCreate = async (values: CreateFormValues) => {
    await createMutation.mutateAsync(values, {
      onSuccess: (response) => {
        addNotification({
          type: 'success',
          title: 'User created',
          message: response.message,
        });
        setCreateOpen(false);
        createForm.reset();
      },
      onError: (error) => {
        const managedError = error as ManagedUserApiError;
        if (managedError.message === 'SOFT_DELETED_USER_EXISTS') {
          setRestoreCandidate(values);
          return;
        }

        addNotification({
          type: 'error',
          title: 'Failed to create user',
          message: error instanceof Error ? error.message : 'Unexpected error',
        });
      },
    });
  };

  const confirmRestoreUser = () => {
    if (!restoreCandidate) return;

    restoreMutation.mutate(restoreCandidate, {
      onSuccess: (response) => {
        addNotification({
          type: 'success',
          title: 'User restored',
          message: response.message,
        });
        setRestoreCandidate(null);
        setCreateOpen(false);
        createForm.reset();
      },
      onError: (error) => {
        addNotification({
          type: 'error',
          title: 'Failed to restore user',
          message: error instanceof Error ? error.message : 'Unexpected error',
        });
        setRestoreCandidate(null);
      },
    });
  };

  const handleResetPassword = (user: ManagedUserListItem) => {
    setResetPasswordUser(user);
  };

  const confirmResetPassword = () => {
    if (!resetPasswordUser) return;

    resetPasswordMutation.mutate(resetPasswordUser.id, {
      onSuccess: (response) => {
        addNotification({
          type: 'success',
          title: 'Password reset sent',
          message: response.message,
        });
        setResetPasswordUser(null);
      },
      onError: (error) => {
        addNotification({
          type: 'error',
          title: 'Failed to send password reset',
          message: error instanceof Error ? error.message : 'Unexpected error',
        });
        setResetPasswordUser(null);
      },
    });
  };

  const handleEditClick = (user: ManagedUserListItem) => {
    setEditingUser(user);
    updateForm.reset({
      full_name: user.full_name,
      group: user.group,
      permissions: user.permissions,
    });
  };

  const handleUpdate = async (values: UpdateFormValues) => {
    if (!editingUser) return;

    await updateMutation.mutateAsync(
      { id: editingUser.id, payload: values },
      {
        onSuccess: () => {
          addNotification({
            type: 'success',
            title: 'User updated',
            message: 'Changes saved successfully',
          });
          setEditingUser(null);
        },
        onError: (error) => {
          addNotification({
            type: 'error',
            title: 'Failed to update user',
            message: error instanceof Error ? error.message : 'Unexpected error',
          });
        },
      },
    );
  };

  const handleToggleStatus = (user: ManagedUserListItem) => {
    setTogglingUser(user);
  };

  const confirmToggleStatus = () => {
    if (!togglingUser) return;
    toggleMutation.mutate(
      { id: togglingUser.id, payload: { is_active: !togglingUser.is_active } },
      {
        onSuccess: () => {
          addNotification({
            type: 'success',
            title: togglingUser.is_active ? 'User deactivated' : 'User activated',
            message: togglingUser.email,
          });
          setTogglingUser(null);
        },
        onError: (error) => {
          addNotification({
            type: 'error',
            title: 'Failed to update status',
            message: error instanceof Error ? error.message : 'Unexpected error',
          });
          setTogglingUser(null);
        },
      },
    );
  };

  const handleDelete = (user: ManagedUserListItem) => {
    setDeletingUser(user);
  };

  const confirmDelete = () => {
    if (!deletingUser) return;
    deleteMutation.mutate(deletingUser.id, {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: 'User deleted',
          message: deletingUser.email,
        });
        setDeletingUser(null);
      },
      onError: (error) => {
        addNotification({
          type: 'error',
          title: 'Failed to delete user',
          message: error instanceof Error ? error.message : 'Unexpected error',
        });
        setDeletingUser(null);
      },
    });
  };

  return (
    <PageContainer
      title="User Management"
      description="Manage users, permissions and activation status"
      header={
        <div className="flex items-center justify-end">
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New user
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="grid gap-3 md:grid-cols-4">
          <Input
            placeholder="Search by email or name"
            value={filters.search ?? ''}
            onChange={(event) =>
              setFilters((previous) => ({
                ...previous,
                search: event.target.value || undefined,
                skip: 0,
              }))
            }
          />

          <Select
            value={filters.group ?? 'all'}
            onValueChange={(value) =>
              setFilters((previous) => ({
                ...previous,
                group: value === 'all' ? undefined : (value as UserGroup),
                skip: 0,
              }))
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Group" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All groups</SelectItem>
              <SelectItem value="admin">Admin</SelectItem>
              <SelectItem value="user">User</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={
              filters.is_active === undefined ? 'all' : filters.is_active ? 'active' : 'inactive'
            }
            onValueChange={(value) =>
              setFilters((previous) => ({
                ...previous,
                is_active:
                  value === 'all' ? undefined : value === 'active' ? true : false,
                skip: 0,
              }))
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={String(filters.limit ?? 20)}
            onValueChange={(value) =>
              setFilters((previous) => ({
                ...previous,
                limit: Number(value),
                skip: 0,
              }))
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Rows" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10</SelectItem>
              <SelectItem value="20">20</SelectItem>
              <SelectItem value="50">50</SelectItem>
              <SelectItem value="100">100</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Group</TableHead>
                <TableHead>Connections</TableHead>
                <TableHead>Datasets</TableHead>
                <TableHead>Devices</TableHead>
                <TableHead>Projects</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {usersQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                    Loading users...
                  </TableCell>
                </TableRow>
              ) : users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                    No users found
                  </TableCell>
                </TableRow>
              ) : (
                users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="font-medium">{user.email}</div>
                      <div className="text-xs text-muted-foreground">{user.full_name}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={user.group === 'admin' ? 'default' : 'secondary'}>
                        {user.group}
                      </Badge>
                    </TableCell>
                    <TableCell>{permissionSummaryBadge(user, 'connections')}</TableCell>
                    <TableCell>{permissionSummaryBadge(user, 'datasets')}</TableCell>
                    <TableCell>{permissionSummaryBadge(user, 'devices')}</TableCell>
                    <TableCell>{permissionSummaryBadge(user, 'projects')}</TableCell>
                    <TableCell>
                      <Badge variant={user.is_active ? 'default' : 'outline'}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                            <span className="sr-only">Open menu</span>
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEditClick(user)}>
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleResetPassword(user)}>
                            <KeyRound className="mr-2 h-4 w-4" />
                            Send new password
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleToggleStatus(user)}>
                            {user.is_active ? 'Deactivate' : 'Activate'}
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-destructive" onClick={() => handleDelete(user)}>
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {(usersQuery.data?.total ?? 0) > 0 && (
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              {(filters.skip ?? 0) + 1}–
              {Math.min((filters.skip ?? 0) + (filters.limit ?? 20), usersQuery.data?.total ?? 0)} of{' '}
              {usersQuery.data?.total ?? 0}
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                disabled={!usersQuery.data?.has_prev}
                onClick={() =>
                  setFilters((previous) => ({
                    ...previous,
                    skip: Math.max(0, (previous.skip ?? 0) - (previous.limit ?? 20)),
                  }))
                }
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                disabled={!usersQuery.data?.has_next}
                onClick={() =>
                  setFilters((previous) => ({
                    ...previous,
                    skip: (previous.skip ?? 0) + (previous.limit ?? 20),
                  }))
                }
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      <CreateUserDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        form={createForm}
        isSubmitting={createMutation.isPending || restoreMutation.isPending}
        onSubmit={handleCreate}
      />

      <ConfirmDialog
        open={!!restoreCandidate}
        onOpenChange={(open) => {
          if (!open) setRestoreCandidate(null);
        }}
        title="User email found in deleted records"
        description={
          <>
            The email <strong>{restoreCandidate?.email}</strong> already exists as a soft-deleted user.
            <br />
            <span className="text-xs text-muted-foreground mt-1 block">
              If you continue, the user account will be restored (is_deleted=false) and a new temporary password will be sent by email.
            </span>
          </>
        }
        confirmLabel="Restore user"
        cancelLabel="Cancel"
        variant="default"
        isLoading={restoreMutation.isPending}
        onConfirm={confirmRestoreUser}
      />

      <EditUserDialog
        open={!!editingUser}
        onOpenChange={(open) => {
          if (!open) setEditingUser(null);
        }}
        form={updateForm}
        userEmail={editingUser?.email ?? ''}
        isSubmitting={updateMutation.isPending}
        onSubmit={handleUpdate}
      />
      <ConfirmDialog
        open={!!deletingUser}
        onOpenChange={(open) => { if (!open) setDeletingUser(null); }}
        title="Delete user"
        description={
          <>
            Are you sure you want to delete <strong>{deletingUser?.email}</strong>?
            <br />
            <span className="text-xs text-muted-foreground mt-1 block">
              This action will soft-delete the user. They will lose access to the platform and their active sessions will be invalidated.
            </span>
          </>
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="destructive"
        isLoading={deleteMutation.isPending}
        onConfirm={confirmDelete}
      />

      <ConfirmDialog
        open={!!togglingUser}
        onOpenChange={(open) => { if (!open) setTogglingUser(null); }}
        title={togglingUser?.is_active ? 'Deactivate user' : 'Activate user'}
        description={
          togglingUser?.is_active ? (
            <>
              Are you sure you want to deactivate <strong>{togglingUser?.email}</strong>?
              <br />
              <span className="text-xs text-muted-foreground mt-1 block">
                The user will not be able to log in or use the platform until reactivated.
              </span>
            </>
          ) : (
            <>
              Are you sure you want to activate <strong>{togglingUser?.email}</strong>?
            </>
          )
        }
        confirmLabel={togglingUser?.is_active ? 'Deactivate' : 'Activate'}
        cancelLabel="Cancel"
        variant={togglingUser?.is_active ? 'destructive' : 'default'}
        isLoading={toggleMutation.isPending}
        onConfirm={confirmToggleStatus}
      />

      <ConfirmDialog
        open={!!resetPasswordUser}
        onOpenChange={(open) => {
          if (!open) setResetPasswordUser(null);
        }}
        title="Send new temporary password"
        description={
          <>
            Send a new temporary password to <strong>{resetPasswordUser?.email}</strong>?
            <br />
            <span className="text-xs text-muted-foreground mt-1 block">
              This will invalidate the previous password and email new credentials to the user.
            </span>
          </>
        }
        confirmLabel="Send password"
        cancelLabel="Cancel"
        variant="default"
        isLoading={resetPasswordMutation.isPending}
        onConfirm={confirmResetPassword}
      />
    </PageContainer>
  );
}

type SharedDialogProps<TFormValues extends { group: UserGroup; permissions: string[] }> = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  form: UseFormReturn<TFormValues>;
  isSubmitting: boolean;
  onSubmit: (values: TFormValues) => Promise<void>;
};

function CreateUserDialog({ open, onOpenChange, form, isSubmitting, onSubmit }: SharedDialogProps<CreateFormValues>) {
  const group = form.watch('group');

  React.useEffect(() => {
    if (group === 'admin') {
      form.setValue('permissions', [
        'connections:write',
        'datasets:write',
        'devices:write',
        'projects:write',
        'users:read',
        'users:write',
      ]);
    }
  }, [group, form]);

  const currentPermissions = form.watch('permissions');
  const permissionFlags = {
    connections: currentPermissions.includes('connections:write'),
    datasets: currentPermissions.includes('datasets:write'),
    devices: currentPermissions.includes('devices:write'),
    projects: currentPermissions.includes('projects:write'),
  };

  const handlePermissionChange = (resource: string, checked: boolean) => {
    const updated = buildUserPermissionsFromMatrix({ ...permissionFlags, [resource]: checked });
    form.setValue('permissions', updated);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create user</DialogTitle>
          <DialogDescription>Create a new platform user and assign initial permissions.</DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="space-y-2">
            <Label htmlFor="create-email">Email</Label>
            <Input id="create-email" {...form.register('email')} />
            {form.formState.errors.email && (
              <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="create-full-name">Full name</Label>
            <Input id="create-full-name" {...form.register('full_name')} />
            {form.formState.errors.full_name && (
              <p className="text-xs text-destructive">{form.formState.errors.full_name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Group</Label>
            <Select value={group} onValueChange={(value) => form.setValue('group', value as UserGroup)}>
              <SelectTrigger>
                <SelectValue placeholder="Select group" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="user">User</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Permissions</Label>
            <div className="grid gap-2 rounded-md border p-3">
              {PERMISSION_RESOURCES.map((resource) => {
                const checked = permissionFlags[resource];
                return (
                  <div key={resource} className="flex items-center justify-between">
                    <span className="text-sm capitalize">{resource}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Write</span>
                      <Checkbox
                        checked={checked}
                        onCheckedChange={(state) => handlePermissionChange(resource, !!state)}
                        disabled={group === 'admin'}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create user'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditUserDialog({
  open,
  onOpenChange,
  form,
  userEmail,
  isSubmitting,
  onSubmit,
}: SharedDialogProps<UpdateFormValues> & { userEmail: string }) {
  const group = form.watch('group');

  React.useEffect(() => {
    if (group === 'admin') {
      form.setValue('permissions', [
        'connections:write',
        'datasets:write',
        'devices:write',
        'projects:write',
        'users:read',
        'users:write',
      ]);
    }
  }, [group, form]);

  const currentPermissions = form.watch('permissions');
  const permissionFlags = {
    connections: currentPermissions.includes('connections:write'),
    datasets: currentPermissions.includes('datasets:write'),
    devices: currentPermissions.includes('devices:write'),
    projects: currentPermissions.includes('projects:write'),
  };

  const handlePermissionChange = (resource: string, checked: boolean) => {
    const updated = buildUserPermissionsFromMatrix({ ...permissionFlags, [resource]: checked });
    form.setValue('permissions', updated);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit user</DialogTitle>
          <DialogDescription>Update group and permissions. Email is immutable.</DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="space-y-2">
            <Label htmlFor="edit-email">Email</Label>
            <Input id="edit-email" value={userEmail} disabled readOnly />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-full-name">Full name</Label>
            <Input id="edit-full-name" {...form.register('full_name')} />
            {form.formState.errors.full_name && (
              <p className="text-xs text-destructive">{form.formState.errors.full_name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Group</Label>
            <Select value={group} onValueChange={(value) => form.setValue('group', value as UserGroup)}>
              <SelectTrigger>
                <SelectValue placeholder="Select group" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="user">User</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Permissions</Label>
            <div className="grid gap-2 rounded-md border p-3">
              {PERMISSION_RESOURCES.map((resource) => {
                const checked = permissionFlags[resource];
                return (
                  <div key={resource} className="flex items-center justify-between">
                    <span className="text-sm capitalize">{resource}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Write</span>
                      <Checkbox
                        checked={checked}
                        onCheckedChange={(state) => handlePermissionChange(resource, !!state)}
                        disabled={group === 'admin'}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
