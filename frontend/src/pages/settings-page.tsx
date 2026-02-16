import React from 'react';
import { Link } from 'react-router-dom';

import { ROUTES } from '@/app/config/constants';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
      <p className="text-muted-foreground">Configure application settings</p>

      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
          <CardDescription>Administrative modules and access control.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="outline">
            <Link to={ROUTES.usersManagement}>Open User Management</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
