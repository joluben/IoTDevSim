import * as React from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { PageContainer } from '@/components/layout/page-container';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { authService } from '@/services/auth.service';
import { useUIStore } from '@/app/store';
import { VALIDATION } from '@/app/config/constants';

const passwordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z
      .string()
      .min(VALIDATION.password.minLength, `Password must be at least ${VALIDATION.password.minLength} characters`)
      .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
      .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
      .regex(/\d/, 'Password must contain at least one number')
      .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character'),
    confirm_password: z.string().min(1, 'Password confirmation is required'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  });

type PasswordFormValues = z.infer<typeof passwordSchema>;

export default function ProfilePage() {
  const addNotification = useUIStore((state) => state.addNotification);

  const profileQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => authService.getCurrentProfile(),
  });

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: (payload: PasswordFormValues) => authService.changePassword(payload),
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: 'Password updated',
        message: 'Your password has been changed successfully.',
      });
      passwordForm.reset();
    },
    onError: (error) => {
      addNotification({
        type: 'error',
        title: 'Failed to change password',
        message: error instanceof Error ? error.message : 'Unexpected error',
      });
    },
  });

  return (
    <PageContainer title="Profile" description="Review your account information and update your password.">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Account details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {profileQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading profile...</p>
            ) : profileQuery.isError ? (
              <Alert variant="destructive">
                <AlertDescription>
                  {profileQuery.error instanceof Error ? profileQuery.error.message : 'Failed to load profile'}
                </AlertDescription>
              </Alert>
            ) : (
              <>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input value={profileQuery.data?.email ?? ''} disabled readOnly />
                </div>

                <div className="space-y-2">
                  <Label>Full name</Label>
                  <Input value={profileQuery.data?.full_name ?? ''} disabled readOnly />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Role</Label>
                    <Input value={profileQuery.data?.is_superuser ? 'admin' : 'user'} disabled readOnly />
                  </div>
                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Input value={profileQuery.data?.is_active ? 'active' : 'inactive'} disabled readOnly />
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Change password</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              onSubmit={passwordForm.handleSubmit((values) => changePasswordMutation.mutate(values))}
            >
              <div className="space-y-2">
                <Label htmlFor="current-password">Current password</Label>
                <Input id="current-password" type="password" {...passwordForm.register('current_password')} />
                {passwordForm.formState.errors.current_password && (
                  <p className="text-xs text-destructive">
                    {passwordForm.formState.errors.current_password.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="new-password">New password</Label>
                <Input id="new-password" type="password" {...passwordForm.register('new_password')} />
                {passwordForm.formState.errors.new_password && (
                  <p className="text-xs text-destructive">
                    {passwordForm.formState.errors.new_password.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-password">Confirm new password</Label>
                <Input id="confirm-password" type="password" {...passwordForm.register('confirm_password')} />
                {passwordForm.formState.errors.confirm_password && (
                  <p className="text-xs text-destructive">
                    {passwordForm.formState.errors.confirm_password.message}
                  </p>
                )}
              </div>

              <Button type="submit" disabled={changePasswordMutation.isPending}>
                {changePasswordMutation.isPending ? 'Updating...' : 'Update password'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
