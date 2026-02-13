import React, { createContext, useContext, useState } from 'react';

type Language = 'es' | 'en';

type Translations = {
  [key in Language]: {
    nav: {
      dashboard: string;
      projects: string;
      devices: string;
      connections: string;
      settings: string;
    };
    auth: {
      login: string;
      register: string;
      forgotPassword: string;
      email: string;
      password: string;
      name: string;
      confirmPassword: string;
      rememberMe: string;
      backToLogin: string;
      createAccount: string;
      alreadyHaveAccount: string;
      sendRecovery: string;
    };
    common: {
      save: string;
      cancel: string;
      delete: string;
      edit: string;
      search: string;
      loading: string;
      submit: string;
      close: string;
      welcome: string;
      profile: string;
      logout: string;
    };
    dashboard: {
      title: string;
      description: string;
      totalDevices: string;
      activeConnections: string;
      runningProjects: string;
      messagesSent: string;
      recentActivity: string;
      systemStatus: string;
      systemHealth: string;
      apiStatus: string;
      database: string;
      healthy: string;
      online: string;
      connected: string;
      noDevices: string;
      noConnections: string;
      noProjects: string;
      noMessages: string;
      noActivity: string;
    };
  };
};

const translations: Translations = {
  es: {
    nav: {
      dashboard: 'Dashboard',
      projects: 'Proyectos',
      devices: 'Dispositivos',
      connections: 'Conexiones',
      settings: 'Configuración'
    },
    auth: {
      login: 'Iniciar Sesión',
      register: 'Registrarse',
      forgotPassword: '¿Olvidaste tu contraseña?',
      email: 'Correo electrónico',
      password: 'Contraseña',
      name: 'Nombre',
      confirmPassword: 'Confirmar contraseña',
      rememberMe: 'Recordarme',
      backToLogin: 'Volver al inicio de sesión',
      createAccount: 'Crear cuenta',
      alreadyHaveAccount: '¿Ya tienes una cuenta?',
      sendRecovery: 'Enviar recuperación'
    },
    common: {
      save: 'Guardar',
      cancel: 'Cancelar',
      delete: 'Eliminar',
      edit: 'Editar',
      search: 'Buscar',
      loading: 'Cargando...',
      submit: 'Enviar',
      close: 'Cerrar',
      welcome: 'Bienvenido',
      profile: 'Perfil',
      logout: 'Cerrar Sesión'
    },
    dashboard: {
      title: 'Dashboard',
      description: 'Bienvenido al Dashboard de IoT-DevSim v2',
      totalDevices: 'Dispositivos Totales',
      activeConnections: 'Conexiones Activas',
      runningProjects: 'Proyectos Ejecutándose',
      messagesSent: 'Mensajes Enviados',
      recentActivity: 'Actividad Reciente',
      systemStatus: 'Estado del Sistema',
      systemHealth: 'Salud del Sistema',
      apiStatus: 'Estado de la API',
      database: 'Base de Datos',
      healthy: 'Saludable',
      online: 'En línea',
      connected: 'Conectado',
      noDevices: 'No hay dispositivos configurados',
      noConnections: 'No hay conexiones activas',
      noProjects: 'No hay proyectos ejecutándose',
      noMessages: 'No se enviaron mensajes hoy',
      noActivity: 'No hay actividad reciente'
    }
  },
  en: {
    nav: {
      dashboard: 'Dashboard',
      projects: 'Projects',
      devices: 'Devices',
      connections: 'Connections',
      settings: 'Settings'
    },
    auth: {
      login: 'Sign In',
      register: 'Sign Up',
      forgotPassword: 'Forgot your password?',
      email: 'Email',
      password: 'Password',
      name: 'Name',
      confirmPassword: 'Confirm password',
      rememberMe: 'Remember me',
      backToLogin: 'Back to login',
      createAccount: 'Create account',
      alreadyHaveAccount: 'Already have an account?',
      sendRecovery: 'Send recovery'
    },
    common: {
      save: 'Save',
      cancel: 'Cancel',
      delete: 'Delete',
      edit: 'Edit',
      search: 'Search',
      loading: 'Loading...',
      submit: 'Submit',
      close: 'Close',
      welcome: 'Welcome',
      profile: 'Profile',
      logout: 'Logout'
    },
    dashboard: {
      title: 'Dashboard',
      description: 'Welcome to IoT-DevSim v2 Dashboard',
      totalDevices: 'Total Devices',
      activeConnections: 'Active Connections',
      runningProjects: 'Running Projects',
      messagesSent: 'Messages Sent',
      recentActivity: 'Recent Activity',
      systemStatus: 'System Status',
      systemHealth: 'System Health',
      apiStatus: 'API Status',
      database: 'Database',
      healthy: 'Healthy',
      online: 'Online',
      connected: 'Connected',
      noDevices: 'No devices configured',
      noConnections: 'No active connections',
      noProjects: 'No projects running',
      noMessages: 'No messages sent today',
      noActivity: 'No recent activity'
    }
  }
};

type I18nContextType = {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: Translations[Language];
};

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<Language>(() => {
    const saved = localStorage.getItem('iot-devsim-language');
    return (saved as Language) || 'es';
  });

  const handleSetLanguage = (lang: Language) => {
    setLanguage(lang);
    localStorage.setItem('iot-devsim-language', lang);
  };

  const value = {
    language,
    setLanguage: handleSetLanguage,
    t: translations[language]
  };

  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}
