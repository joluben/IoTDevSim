import * as React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Save } from 'lucide-react';

import { PageContainer } from '@/components/layout/page-container';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useProject,
  useCreateProject,
  useUpdateProject,
} from '@/hooks/useProjects';
import { useConnections } from '@/hooks/useConnections';
import { projectFormSchema, type ProjectFormValues } from '@/types/project';
import type { Connection } from '@/types/connection';
import { useUIStore } from '@/app/store/ui-store';

export default function ProjectFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const addNotification = useUIStore((s) => s.addNotification);
  const isEdit = !!id;

  const projectQuery = useProject(id ?? '');
  const createMutation = useCreateProject();
  const updateMutation = useUpdateProject();
  const connectionsQuery = useConnections({});

  const form = useForm<ProjectFormValues>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: {
      name: '',
      description: '',
      tags: '',
      connection_id: '',
      auto_reset_counter: false,
      max_devices: 1000,
    },
  });

  // Populate form for edit mode
  React.useEffect(() => {
    if (isEdit && projectQuery.data) {
      const p = projectQuery.data;
      form.reset({
        name: p.name,
        description: p.description || '',
        tags: (p.tags || []).join(', '),
        connection_id: p.connection_id || '',
        auto_reset_counter: p.auto_reset_counter,
        max_devices: p.max_devices,
      });
    }
  }, [isEdit, projectQuery.data, form]);

  const onSubmit = (values: ProjectFormValues) => {
    const tags = values.tags
      ? values.tags.split(',').map((t) => t.trim()).filter(Boolean)
      : [];

    const payload = {
      name: values.name,
      description: values.description || undefined,
      tags,
      connection_id: values.connection_id || undefined,
      auto_reset_counter: values.auto_reset_counter,
      max_devices: values.max_devices,
    };

    if (isEdit) {
      updateMutation.mutate(
        { id: id!, payload },
        {
          onSuccess: () => {
            addNotification({ type: 'success', title: 'Project updated', message: '' });
            navigate(`/projects/${id}`);
          },
          onError: (err) =>
            addNotification({
              type: 'error',
              title: 'Failed to update project',
              message: err instanceof Error ? err.message : 'Unknown error',
            }),
        }
      );
    } else {
      createMutation.mutate(payload, {
        onSuccess: (project) => {
          addNotification({ type: 'success', title: 'Project created', message: '' });
          navigate(`/projects/${project.id}`);
        },
        onError: (err) =>
          addNotification({
            type: 'error',
            title: 'Failed to create project',
            message: err instanceof Error ? err.message : 'Unknown error',
          }),
      });
    }
  };

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  if (isEdit && projectQuery.isLoading) {
    return (
      <PageContainer title="Loading..." description="">
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      </PageContainer>
    );
  }

  const connections = connectionsQuery.data?.items ?? [];

  return (
    <PageContainer
      title={isEdit ? 'Edit Project' : 'New Project'}
      description={isEdit ? 'Update project settings' : 'Create a new project to group devices'}
      header={
        <Button variant="ghost" size="sm" onClick={() => navigate('/projects')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Projects
        </Button>
      }
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 max-w-2xl">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">General Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name *</FormLabel>
                    <FormControl>
                      <Input placeholder="My IoT Project" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Optional project description..."
                        rows={3}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="tags"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tags</FormLabel>
                    <FormControl>
                      <Input placeholder="production, sensors, factory-a" {...field} />
                    </FormControl>
                    <FormDescription>Comma-separated tags for organization</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Transmission Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="connection_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Default Connection</FormLabel>
                    <Select
                      onValueChange={(val) => field.onChange(val === '__none__' ? '' : val)}
                      value={field.value || '__none__'}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Use each device's own connection" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="__none__">No default (use device connection)</SelectItem>
                        {connections.map((conn: Connection) => (
                          <SelectItem key={conn.id} value={conn.id}>
                            {conn.name} ({conn.protocol})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      If set, all project devices will use this connection when transmitting
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="auto_reset_counter"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">Auto Reset Counter</FormLabel>
                      <FormDescription>
                        Automatically reset the row index when reaching the end of a dataset
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="max_devices"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Max Devices</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
                        max={10000}
                        {...field}
                        onChange={(e) => field.onChange(Number(e.target.value))}
                      />
                    </FormControl>
                    <FormDescription>Maximum number of devices in this project</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={isSubmitting}>
              <Save className="h-4 w-4 mr-2" />
              {isSubmitting
                ? 'Saving...'
                : isEdit
                  ? 'Update Project'
                  : 'Create Project'}
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate('/projects')}>
              Cancel
            </Button>
          </div>
        </form>
      </Form>
    </PageContainer>
  );
}
