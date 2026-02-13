/**
 * Generate Dataset Dialog Component
 * Allows users to create synthetic datasets using predefined generators
 */

import * as React from 'react';
import {
    Cpu,
    X,
    Wand2,
    Thermometer,
    Settings2,
    Activity,
    Wind,
    Truck,
    ChevronRight,
    ChevronLeft,
    Check,
    AlertCircle,
    Info,
    LayoutDashboard,
    Loader2,
    Plus,
    Trash2,
} from 'lucide-react';
import { useForm } from 'react-hook-form';

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useGenerateDataset, useGeneratorTypes } from '@/hooks/useDatasets';
import { useUIStore } from '@/app/store/ui-store';
import type { GeneratorType, DatasetGenerateRequest } from '@/types/dataset';

interface GenerateDatasetDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

const GENERATOR_TEMPLATES = [
    {
        id: 'temperature' as GeneratorType,
        name: 'Sensores de Temperatura',
        description: 'Simula una red de sensores de temperatura con ciclos circadianos y ruido estocástico.',
        icon: Thermometer,
        color: 'text-orange-500',
        bgColor: 'bg-orange-500/10',
    },
    {
        id: 'equipment' as GeneratorType,
        name: 'Estado de Maquinaria',
        description: 'Genera datos de telemetría industrial incluyendo vibración, consumo y ciclos de mantenimiento.',
        icon: Activity,
        color: 'text-blue-500',
        bgColor: 'bg-blue-500/10',
    },
    {
        id: 'environmental' as GeneratorType,
        name: 'Estación Ambiental',
        description: 'Simula variables como humedad, CO2, presión atmosférica y calidad del aire.',
        icon: Wind,
        color: 'text-green-500',
        bgColor: 'bg-green-500/10',
    },
    {
        id: 'fleet' as GeneratorType,
        name: 'Telemetría de Flota',
        description: 'Datos de geolocalización, consumo de combustible y comportamiento del conductor para vehículos.',
        icon: Truck,
        color: 'text-purple-500',
        bgColor: 'bg-purple-500/10',
    },
    {
        id: 'custom' as GeneratorType,
        name: 'Generador Personalizado',
        description: 'Define tus propias columnas y reglas de generación mediante esquemas JSON.',
        icon: Settings2,
        color: 'text-gray-500',
        bgColor: 'bg-gray-500/10',
    },
];

export function GenerateDatasetDialog({ open, onOpenChange }: GenerateDatasetDialogProps) {
    const [step, setStep] = React.useState(1);
    const [selectedType, setSelectedType] = React.useState<GeneratorType | null>(null);
    const generateMutation = useGenerateDataset();
    const addNotification = useUIStore((s) => s.addNotification);

    const form = useForm<DatasetGenerateRequest>({
        defaultValues: {
            name: '',
            description: '',
            generator_type: 'temperature',
            generator_config: {
                sensor_count: 5,
                duration_days: 7,
                sampling_interval: 300,
            },
            tags: ['synthetic'],
        },
    });

    const onSubmit = (data: DatasetGenerateRequest) => {
        if (!selectedType) return;

        generateMutation.mutate({
            ...data,
            generator_type: selectedType,
        }, {
            onSuccess: () => {
                addNotification({
                    type: 'success',
                    title: 'Generación iniciada',
                    message: 'El dataset sintético se está generando en segundo plano.',
                });
                resetAndClose();
            },
            onError: (error) => {
                addNotification({
                    type: 'error',
                    title: 'Error de generación',
                    message: error instanceof Error ? error.message : 'No se pudo generar el dataset.',
                });
            }
        });
    };

    const resetAndClose = () => {
        setStep(1);
        setSelectedType(null);
        form.reset();
        onOpenChange(false);
    };

    const nextStep = () => {
        if (step === 1 && !selectedType) return;
        setStep(step + 1);
    };

    const prevStep = () => setStep(step - 1);

    return (
        <Dialog open={open} onOpenChange={(val) => !val && resetAndClose()}>
            <DialogContent className="max-w-2xl overflow-hidden p-0 flex flex-col max-h-[90vh]">
                <DialogHeader className="p-6 pb-2">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            <Wand2 className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                            <DialogTitle className="text-xl">Generar Datos Sintéticos</DialogTitle>
                            <DialogDescription>
                                Crea un conjunto de datos realista para tus pruebas de simulación.
                            </DialogDescription>
                        </div>
                    </div>
                </DialogHeader>

                <div className="flex-1 min-h-0 overflow-hidden">
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="h-full flex flex-col">
                            <ScrollArea className="flex-1 min-h-0 px-6 pb-6">
                                {step === 1 ? (
                                    <div className="space-y-4 pt-4">
                                        <div className="grid grid-cols-1 gap-3">
                                            {GENERATOR_TEMPLATES.map((item) => (
                                                <Card
                                                    key={item.id}
                                                    className={`cursor-pointer transition-all border-2 ${selectedType === item.id ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'hover:border-primary/50 bg-card'}`}
                                                    onClick={() => {
                                                        setSelectedType(item.id);
                                                        form.setValue('generator_type', item.id);
                                                        // Set type-specific defaults
                                                        const defaults: Record<string, any> = {
                                                            temperature: { sensor_count: 5, duration_days: 7, sampling_interval: 300, base_temperature: 22.0, variation_range: 5.0, add_noise: true },
                                                            equipment: { equipment_types: ['pump', 'motor'], equipment_count: 3, duration_days: 7, sampling_interval: 3600 },
                                                            environmental: { location_count: 5, parameters: ['co2', 'humidity', 'pressure'], duration_days: 7, sampling_interval: 900 },
                                                            fleet: { vehicle_count: 10, duration_days: 3, sampling_interval: 60, base_latitude: 40.7128, base_longitude: -74.006 },
                                                            custom: {
                                                                row_count: 100,
                                                                columns: [
                                                                    { name: 'id', generator: 'sequential', params: { start: 1, step: 1, prefix: 'ROW-' } },
                                                                    { name: 'timestamp', generator: 'timestamp', params: { interval_seconds: 60 } },
                                                                    { name: 'value', generator: 'random_float', params: { min: 0, max: 100, decimals: 2 } },
                                                                ],
                                                            },
                                                        };
                                                        form.setValue('generator_config', defaults[item.id] || {});
                                                    }}
                                                >
                                                    <CardContent className="p-4 flex items-center gap-4">
                                                        <div className={`p-3 rounded-lg ${item.bgColor} ${item.color}`}>
                                                            <item.icon className="h-6 w-6" />
                                                        </div>
                                                        <div className="flex-1 space-y-1">
                                                            <div className="flex items-center justify-between">
                                                                <h4 className="font-bold text-sm">{item.name}</h4>
                                                                {selectedType === item.id && <Check className="h-4 w-4 text-primary" />}
                                                            </div>
                                                            <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                                                                {item.description}
                                                            </p>
                                                        </div>
                                                    </CardContent>
                                                </Card>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-6 pt-4">
                                        <div className="space-y-4">
                                            <h4 className="text-sm font-bold flex items-center gap-2 text-primary">
                                                <LayoutDashboard className="h-4 w-4" />
                                                Información Básica
                                            </h4>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                <FormField
                                                    control={form.control}
                                                    name="name"
                                                    rules={{ required: 'El nombre es obligatorio' }}
                                                    render={({ field }) => (
                                                        <FormItem>
                                                            <FormLabel>Nombre del Dataset *</FormLabel>
                                                            <FormControl>
                                                                <Input placeholder="Ej: Simulación Sensores Edificio A" {...field} />
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
                                                            <FormLabel>Etiquetas</FormLabel>
                                                            <FormControl>
                                                                <Input
                                                                    placeholder="playwright, test"
                                                                    value={Array.isArray(field.value) ? field.value.join(', ') : ''}
                                                                    onChange={(e) => field.onChange(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                                                                />
                                                            </FormControl>
                                                            <FormMessage />
                                                        </FormItem>
                                                    )}
                                                />
                                            </div>
                                            <FormField
                                                control={form.control}
                                                name="description"
                                                render={({ field }) => (
                                                    <FormItem>
                                                        <FormLabel>Descripción</FormLabel>
                                                        <FormControl>
                                                            <Input placeholder="Descripción opcional" {...field} value={field.value || ''} />
                                                        </FormControl>
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />
                                        </div>

                                        <div className="space-y-4 border-t pt-4">
                                            <h4 className="text-sm font-bold flex items-center gap-2 text-primary">
                                                <Settings2 className="h-4 w-4" />
                                                Configuración del Generador: <span className="text-muted-foreground font-normal italic">{GENERATOR_TEMPLATES.find(t => t.id === selectedType)?.name}</span>
                                            </h4>

                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                {selectedType === 'temperature' && (
                                                    <>
                                                        <FormItem>
                                                            <FormLabel>Cantidad de Sensores</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.sensor_count', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Número de sensores de temperatura.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Duración (Días)</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.duration_days', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Rango de tiempo total de los datos.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Intervalo (Segundos)</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.sampling_interval', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Frecuencia de muestreo (ej: 300 = cada 5 min).</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Temperatura Base (°C)</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" step="0.1" {...form.register('generator_config.base_temperature', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Temperatura media de referencia.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Rango de Variación (°C)</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" step="0.1" {...form.register('generator_config.variation_range', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Amplitud de la variación diaria.</FormDescription>
                                                        </FormItem>
                                                        <div className="flex items-end pb-2">
                                                            <div className="flex items-center space-x-2 bg-muted/50 p-2 rounded-lg w-full border border-dashed">
                                                                <Switch id="noise" defaultChecked onCheckedChange={(v) => form.setValue('generator_config.add_noise', v)} />
                                                                <div className="grid gap-1.5 leading-none">
                                                                    <label htmlFor="noise" className="text-xs font-medium leading-none">Agregar Ruido Realista</label>
                                                                    <p className="text-[10px] text-muted-foreground">Simula imperfecciones estocásticas.</p>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </>
                                                )}

                                                {selectedType === 'equipment' && (
                                                    <>
                                                        <FormItem>
                                                            <FormLabel>Tipos de Equipo</FormLabel>
                                                            <FormControl>
                                                                <Input
                                                                    placeholder="pump, motor, compressor"
                                                                    defaultValue="pump, motor"
                                                                    onChange={(e) => form.setValue('generator_config.equipment_types', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                                                                />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Tipos de maquinaria separados por coma.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Equipos por Tipo</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.equipment_count', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Cantidad de equipos por cada tipo.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Duración (Días)</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.duration_days', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Rango de tiempo de los datos.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Intervalo (Segundos)</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.sampling_interval', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Frecuencia de muestreo.</FormDescription>
                                                        </FormItem>
                                                    </>
                                                )}

                                                {selectedType === 'environmental' && (
                                                    <>
                                                        <FormItem>
                                                            <FormLabel>Cantidad de Estaciones</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.location_count', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Número de estaciones de monitoreo.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Parámetros</FormLabel>
                                                            <FormControl>
                                                                <Input
                                                                    placeholder="co2, humidity, pressure, temperature"
                                                                    defaultValue="co2, humidity, pressure"
                                                                    onChange={(e) => form.setValue('generator_config.parameters', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                                                                />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Variables ambientales separadas por coma.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Duración (Días)</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.duration_days', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Rango de tiempo de los datos.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Intervalo (Segundos)</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.sampling_interval', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Frecuencia de muestreo.</FormDescription>
                                                        </FormItem>
                                                    </>
                                                )}

                                                {selectedType === 'fleet' && (
                                                    <>
                                                        <FormItem>
                                                            <FormLabel>Cantidad de Vehículos</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.vehicle_count', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Número de vehículos en la flota.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Duración (Días)</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.duration_days', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Rango de tiempo de los datos.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Intervalo (Segundos)</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" {...form.register('generator_config.sampling_interval', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Frecuencia de muestreo.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Latitud Base</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" step="0.0001" {...form.register('generator_config.base_latitude', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Centro geográfico de la flota.</FormDescription>
                                                        </FormItem>
                                                        <FormItem>
                                                            <FormLabel>Longitud Base</FormLabel>
                                                            <FormControl>
                                                                <Input type="number" step="0.0001" {...form.register('generator_config.base_longitude', { valueAsNumber: true })} />
                                                            </FormControl>
                                                            <FormDescription className="text-[10px]">Centro geográfico de la flota.</FormDescription>
                                                        </FormItem>
                                                    </>
                                                )}

                                                {selectedType === 'custom' && (() => {
                                                    const config = form.watch('generator_config') || { columns: [], row_count: 100 };
                                                    const columns: Array<{ name: string; generator: string; params: Record<string, any> }> = Array.isArray(config.columns) ? config.columns : [];
                                                    const GENERATOR_OPTIONS = [
                                                        { value: 'random_int', label: 'Entero aleatorio' },
                                                        { value: 'random_float', label: 'Decimal aleatorio' },
                                                        { value: 'random_choice', label: 'Selección aleatoria' },
                                                        { value: 'sequential', label: 'Secuencial' },
                                                        { value: 'timestamp', label: 'Timestamp' },
                                                        { value: 'uuid', label: 'UUID' },
                                                        { value: 'normal_distribution', label: 'Distribución normal' },
                                                        { value: 'constant', label: 'Constante' },
                                                    ];
                                                    const updateColumns = (newCols: typeof columns) => {
                                                        form.setValue('generator_config', { ...config, columns: newCols });
                                                    };
                                                    const addColumn = () => {
                                                        updateColumns([...columns, { name: '', generator: 'random_float', params: { min: 0, max: 100, decimals: 2 } }]);
                                                    };
                                                    const removeColumn = (idx: number) => {
                                                        updateColumns(columns.filter((_, i) => i !== idx));
                                                    };
                                                    const updateColumn = (idx: number, field: string, value: any) => {
                                                        const updated = [...columns];
                                                        if (field === 'name' || field === 'generator') {
                                                            (updated[idx] as any)[field] = value;
                                                            if (field === 'generator') {
                                                                const defaultParams: Record<string, any> = {
                                                                    random_int: { min: 0, max: 100 },
                                                                    random_float: { min: 0, max: 100, decimals: 2 },
                                                                    random_choice: { choices: ['A', 'B', 'C'] },
                                                                    sequential: { start: 1, step: 1, prefix: '' },
                                                                    timestamp: { interval_seconds: 60 },
                                                                    uuid: {},
                                                                    normal_distribution: { mean: 0, std: 1, decimals: 2 },
                                                                    constant: { value: '' },
                                                                };
                                                                updated[idx].params = defaultParams[value] || {};
                                                            }
                                                        } else {
                                                            updated[idx].params = { ...updated[idx].params, [field]: value };
                                                        }
                                                        updateColumns(updated);
                                                    };
                                                    return (
                                                        <>
                                                            <FormItem>
                                                                <FormLabel>Cantidad de Filas</FormLabel>
                                                                <FormControl>
                                                                    <Input
                                                                        type="number"
                                                                        value={String(config.row_count || 100)}
                                                                        onChange={(e) => form.setValue('generator_config', { ...config, row_count: parseInt(e.target.value) || 100 })}
                                                                    />
                                                                </FormControl>
                                                                <FormDescription className="text-[10px]">Número de filas a generar (1 - 1,000,000).</FormDescription>
                                                            </FormItem>
                                                            <div className="col-span-2 space-y-3">
                                                                <div className="flex items-center justify-between">
                                                                    <FormLabel>Columnas ({columns.length})</FormLabel>
                                                                    <Button type="button" variant="outline" size="sm" onClick={addColumn}>
                                                                        <Plus className="h-3 w-3 mr-1" /> Añadir
                                                                    </Button>
                                                                </div>
                                                                {columns.map((col, idx) => (
                                                                    <div key={idx} className="rounded-lg border bg-muted/30 p-3 space-y-2">
                                                                        <div className="flex items-center gap-2">
                                                                            <Input
                                                                                placeholder="Nombre columna"
                                                                                value={col.name}
                                                                                onChange={(e) => updateColumn(idx, 'name', e.target.value)}
                                                                                className="flex-1 h-8 text-xs"
                                                                            />
                                                                            <select
                                                                                value={col.generator}
                                                                                onChange={(e) => updateColumn(idx, 'generator', e.target.value)}
                                                                                className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                                                                            >
                                                                                {GENERATOR_OPTIONS.map((opt) => (
                                                                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                                                                ))}
                                                                            </select>
                                                                            <Button type="button" variant="ghost" size="icon" className="h-8 w-8 shrink-0 text-destructive" onClick={() => removeColumn(idx)}>
                                                                                <Trash2 className="h-3.5 w-3.5" />
                                                                            </Button>
                                                                        </div>
                                                                        {(col.generator === 'random_int' || col.generator === 'random_float') && (
                                                                            <div className="flex gap-2">
                                                                                <Input type="number" placeholder="Min" value={col.params.min ?? 0} onChange={(e) => updateColumn(idx, 'min', parseFloat(e.target.value))} className="h-7 text-xs" />
                                                                                <Input type="number" placeholder="Max" value={col.params.max ?? 100} onChange={(e) => updateColumn(idx, 'max', parseFloat(e.target.value))} className="h-7 text-xs" />
                                                                                {col.generator === 'random_float' && (
                                                                                    <Input type="number" placeholder="Decimales" value={col.params.decimals ?? 2} onChange={(e) => updateColumn(idx, 'decimals', parseInt(e.target.value))} className="h-7 text-xs w-20" />
                                                                                )}
                                                                            </div>
                                                                        )}
                                                                        {col.generator === 'random_choice' && (
                                                                            <Input
                                                                                placeholder="Opciones separadas por coma"
                                                                                value={Array.isArray(col.params.choices) ? col.params.choices.join(', ') : ''}
                                                                                onChange={(e) => updateColumn(idx, 'choices', e.target.value.split(',').map((s: string) => s.trim()).filter(Boolean))}
                                                                                className="h-7 text-xs"
                                                                            />
                                                                        )}
                                                                        {col.generator === 'sequential' && (
                                                                            <div className="flex gap-2">
                                                                                <Input type="number" placeholder="Inicio" value={col.params.start ?? 1} onChange={(e) => updateColumn(idx, 'start', parseInt(e.target.value))} className="h-7 text-xs" />
                                                                                <Input type="number" placeholder="Paso" value={col.params.step ?? 1} onChange={(e) => updateColumn(idx, 'step', parseInt(e.target.value))} className="h-7 text-xs" />
                                                                                <Input placeholder="Prefijo" value={col.params.prefix ?? ''} onChange={(e) => updateColumn(idx, 'prefix', e.target.value)} className="h-7 text-xs" />
                                                                            </div>
                                                                        )}
                                                                        {col.generator === 'timestamp' && (
                                                                            <Input type="number" placeholder="Intervalo (seg)" value={col.params.interval_seconds ?? 60} onChange={(e) => updateColumn(idx, 'interval_seconds', parseInt(e.target.value))} className="h-7 text-xs" />
                                                                        )}
                                                                        {col.generator === 'normal_distribution' && (
                                                                            <div className="flex gap-2">
                                                                                <Input type="number" placeholder="Media" value={col.params.mean ?? 0} onChange={(e) => updateColumn(idx, 'mean', parseFloat(e.target.value))} className="h-7 text-xs" />
                                                                                <Input type="number" placeholder="Desv. Std" value={col.params.std ?? 1} onChange={(e) => updateColumn(idx, 'std', parseFloat(e.target.value))} className="h-7 text-xs" />
                                                                                <Input type="number" placeholder="Decimales" value={col.params.decimals ?? 2} onChange={(e) => updateColumn(idx, 'decimals', parseInt(e.target.value))} className="h-7 text-xs w-20" />
                                                                            </div>
                                                                        )}
                                                                        {col.generator === 'constant' && (
                                                                            <Input placeholder="Valor constante" value={col.params.value ?? ''} onChange={(e) => updateColumn(idx, 'value', e.target.value)} className="h-7 text-xs" />
                                                                        )}
                                                                    </div>
                                                                ))}
                                                                {columns.length === 0 && (
                                                                    <div className="text-center py-4 text-xs text-muted-foreground border rounded-lg border-dashed">
                                                                        Añade al menos una columna para generar datos.
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </>
                                                    );
                                                })()}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </ScrollArea>

                            <DialogFooter className="p-6 border-t bg-muted/20">
                                {step === 1 ? (
                                    <>
                                        <Button variant="outline" type="button" onClick={resetAndClose}>
                                            Cancelar
                                        </Button>
                                        <Button
                                            type="button"
                                            onClick={nextStep}
                                            disabled={!selectedType}
                                            className="group"
                                        >
                                            Siguiente: Configurar
                                            <ChevronRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                                        </Button>
                                    </>
                                ) : (
                                    <>
                                        <Button variant="ghost" type="button" onClick={prevStep}>
                                            <ChevronLeft className="mr-2 h-4 w-4" />
                                            Atrás
                                        </Button>
                                        <Button
                                            type="submit"
                                            disabled={generateMutation.isPending}
                                            className="min-w-[120px]"
                                        >
                                            {generateMutation.isPending ? (
                                                <>
                                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                    Generando...
                                                </>
                                            ) : (
                                                <>
                                                    <Cpu className="mr-2 h-4 w-4" />
                                                    Crear Dataset
                                                </>
                                            )}
                                        </Button>
                                    </>
                                )}
                            </DialogFooter>
                        </form>
                    </Form>
                </div>
            </DialogContent>
        </Dialog>
    );
}
