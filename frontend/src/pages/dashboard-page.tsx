import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DashboardPage as DashboardPageContainer } from '@/components/layout/page-container';
import { Button } from '@/components/ui/button';
import { Plus, Activity, Zap, Database } from 'lucide-react';
import { useI18n } from '@/contexts/i18n-context';

export default function DashboardPage() {
  const { t } = useI18n();
  
  const handleCreateDevice = () => {
    console.log('Create device clicked');
  };

  const handleCreateConnection = () => {
    console.log('Create connection clicked');
  };

  const widgets = (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">
            {t.dashboard.totalDevices}
          </CardTitle>
          <Database className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">0</div>
          <p className="text-xs text-muted-foreground">
            {t.dashboard.noDevices}
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">
            {t.dashboard.activeConnections}
          </CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">0</div>
          <p className="text-xs text-muted-foreground">
            {t.dashboard.noConnections}
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">
            {t.dashboard.runningProjects}
          </CardTitle>
          <Zap className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">0</div>
          <p className="text-xs text-muted-foreground">
            {t.dashboard.noProjects}
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">
            {t.dashboard.messagesSent}
          </CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">0</div>
          <p className="text-xs text-muted-foreground">
            {t.dashboard.noMessages}
          </p>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <DashboardPageContainer
      title={t.dashboard.title}
      description={t.dashboard.description}
      showBreadcrumb={false}
      widgets={widgets}
      actions={[
        {
          label: 'New Connection',
          onClick: handleCreateConnection,
          variant: 'outline',
          icon: Plus,
        },
      ]}
      primaryAction={{
        label: 'New Device',
        onClick: handleCreateDevice,
        icon: Plus,
      }}
    >
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t.dashboard.recentActivity}</CardTitle>
            <CardDescription>
              Latest events from your IoT devices
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8 text-muted-foreground">
              {t.dashboard.noActivity}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>{t.dashboard.systemStatus}</CardTitle>
            <CardDescription>
              Overall system health and performance
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">{t.dashboard.systemHealth}</span>
                <span className="text-sm font-medium text-green-600">{t.dashboard.healthy}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">{t.dashboard.apiStatus}</span>
                <span className="text-sm font-medium text-green-600">{t.dashboard.online}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">{t.dashboard.database}</span>
                <span className="text-sm font-medium text-green-600">{t.dashboard.connected}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardPageContainer>
  );
}
