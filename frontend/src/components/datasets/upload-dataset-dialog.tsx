/**
 * Upload Dataset Dialog
 * Dialog for uploading files to create new datasets
 */

import * as React from 'react';
import { Upload, FileSpreadsheet, X, AlertCircle, CheckCircle } from 'lucide-react';

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useUploadDataset } from '@/hooks/useDatasets';
import { useUIStore } from '@/app/store/ui-store';
import type { DatasetUploadRequest } from '@/types/dataset';

interface UploadDatasetDialogProps {
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
    trigger?: React.ReactNode;
}

const ACCEPTED_FORMATS = '.csv,.xlsx,.xls,.json,.tsv';
const MAX_FILE_SIZE = 150 * 1024 * 1024; // 150MB

function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function UploadDatasetDialog({
    open: controlledOpen,
    onOpenChange,
    trigger,
}: UploadDatasetDialogProps) {
    const [internalOpen, setInternalOpen] = React.useState(false);
    const open = controlledOpen ?? internalOpen;
    const setOpen = onOpenChange ?? setInternalOpen;

    const [file, setFile] = React.useState<File | null>(null);
    const [name, setName] = React.useState('');
    const [description, setDescription] = React.useState('');
    const [tags, setTags] = React.useState('');
    const [hasHeader, setHasHeader] = React.useState(true);
    const [delimiter, setDelimiter] = React.useState(',');
    const [encoding, setEncoding] = React.useState('utf-8');
    const [error, setError] = React.useState<string | null>(null);
    const [dragOver, setDragOver] = React.useState(false);

    const uploadMutation = useUploadDataset();
    const addNotification = useUIStore((s) => s.addNotification);
    const fileInputRef = React.useRef<HTMLInputElement>(null);

    const handleFileSelect = (selectedFile: File) => {
        setError(null);

        // Validate file size
        if (selectedFile.size > MAX_FILE_SIZE) {
            setError(`El archivo excede el límite de ${formatBytes(MAX_FILE_SIZE)}`);
            return;
        }

        // Validate file type
        const extension = selectedFile.name.split('.').pop()?.toLowerCase();
        if (!['csv', 'xlsx', 'xls', 'json', 'tsv'].includes(extension || '')) {
            setError('Formato de archivo no soportado');
            return;
        }

        setFile(selectedFile);

        // Auto-set name from filename
        if (!name) {
            const baseName = selectedFile.name.replace(/\.[^/.]+$/, '');
            setName(baseName);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);

        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile) {
            handleFileSelect(droppedFile);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(true);
    };

    const handleDragLeave = () => {
        setDragOver(false);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!file || !name) return;

        const metadata: DatasetUploadRequest = {
            name: name.trim(),
            description: description.trim() || undefined,
            tags: tags ? tags.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean) : [],
            has_header: hasHeader,
            delimiter,
            encoding,
        };

        try {
            await uploadMutation.mutateAsync({ file, metadata });
            addNotification({
                type: 'success',
                title: 'Dataset subido',
                message: `El dataset "${name}" se ha creado correctamente.`,
            });
            handleReset();
            setOpen(false);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Error al subir el archivo';
            setError(message);
        }
    };

    const handleReset = () => {
        setFile(null);
        setName('');
        setDescription('');
        setTags('');
        setHasHeader(true);
        setDelimiter(',');
        setEncoding('utf-8');
        setError(null);
    };

    const handleOpenChange = (newOpen: boolean) => {
        if (!newOpen) {
            handleReset();
        }
        setOpen(newOpen);
    };

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
            <DialogContent className="sm:max-w-[500px]">
                <form onSubmit={handleSubmit}>
                    <DialogHeader>
                        <DialogTitle>Subir Dataset</DialogTitle>
                        <DialogDescription>
                            Sube un archivo CSV, Excel o JSON para crear un nuevo dataset.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        {/* File drop zone */}
                        <div
                            className={`relative rounded-lg border-2 border-dashed p-8 text-center transition-colors ${dragOver
                                    ? 'border-primary bg-primary/5'
                                    : file
                                        ? 'border-green-500 bg-green-500/5'
                                        : 'border-muted-foreground/25 hover:border-primary/50'
                                }`}
                            onDrop={handleDrop}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                        >
                            {file ? (
                                <div className="flex items-center justify-center gap-3">
                                    <FileSpreadsheet className="h-8 w-8 text-green-500" />
                                    <div className="text-left">
                                        <p className="font-medium">{file.name}</p>
                                        <p className="text-sm text-muted-foreground">
                                            {formatBytes(file.size)}
                                        </p>
                                    </div>
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => setFile(null)}
                                    >
                                        <X className="h-4 w-4" />
                                    </Button>
                                </div>
                            ) : (
                                <>
                                    <Upload className="mx-auto h-10 w-10 text-muted-foreground" />
                                    <p className="mt-2 text-sm text-muted-foreground">
                                        Arrastra un archivo aquí o{' '}
                                        <button
                                            type="button"
                                            className="text-primary underline"
                                            onClick={() => fileInputRef.current?.click()}
                                        >
                                            selecciona uno
                                        </button>
                                    </p>
                                    <p className="mt-1 text-xs text-muted-foreground">
                                        CSV, Excel, JSON hasta {formatBytes(MAX_FILE_SIZE)}
                                    </p>
                                </>
                            )}
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept={ACCEPTED_FORMATS}
                                className="hidden"
                                onChange={(e) => {
                                    const f = e.target.files?.[0];
                                    if (f) handleFileSelect(f);
                                }}
                            />
                        </div>

                        {/* Error alert */}
                        {error && (
                            <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                        )}

                        {/* Name input */}
                        <div className="space-y-2">
                            <Label htmlFor="name">Nombre *</Label>
                            <Input
                                id="name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="Nombre del dataset"
                                required
                            />
                        </div>

                        {/* Description */}
                        <div className="space-y-2">
                            <Label htmlFor="description">Descripción</Label>
                            <Textarea
                                id="description"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Descripción opcional del dataset"
                                rows={2}
                            />
                        </div>

                        {/* Tags */}
                        <div className="space-y-2">
                            <Label htmlFor="tags">Etiquetas</Label>
                            <Input
                                id="tags"
                                value={tags}
                                onChange={(e) => setTags(e.target.value)}
                                placeholder="Separadas por coma: sensor, temperatura"
                            />
                        </div>

                        {/* CSV options */}
                        <div className="space-y-4 rounded-lg border p-4">
                            <h4 className="text-sm font-medium">Opciones de archivo</h4>

                            <div className="flex items-center justify-between">
                                <Label htmlFor="hasHeader">Tiene encabezado</Label>
                                <Switch
                                    id="hasHeader"
                                    checked={hasHeader}
                                    onCheckedChange={setHasHeader}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="delimiter">Delimitador</Label>
                                    <Select value={delimiter} onValueChange={setDelimiter}>
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value=",">Coma (,)</SelectItem>
                                            <SelectItem value=";">Punto y coma (;)</SelectItem>
                                            <SelectItem value="\t">Tabulador</SelectItem>
                                            <SelectItem value="|">Pipe (|)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="encoding">Codificación</Label>
                                    <Select value={encoding} onValueChange={setEncoding}>
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="utf-8">UTF-8</SelectItem>
                                            <SelectItem value="latin-1">Latin-1</SelectItem>
                                            <SelectItem value="iso-8859-1">ISO-8859-1</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        </div>

                        {/* Upload progress */}
                        {uploadMutation.isPending && (
                            <div className="space-y-2">
                                <div className="flex items-center justify-between text-sm">
                                    <span>Subiendo...</span>
                                </div>
                                <Progress value={undefined} className="h-2" />
                            </div>
                        )}
                    </div>

                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => handleOpenChange(false)}
                        >
                            Cancelar
                        </Button>
                        <Button
                            type="submit"
                            disabled={!file || !name || uploadMutation.isPending}
                        >
                            {uploadMutation.isPending ? 'Subiendo...' : 'Subir Dataset'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
