module.exports = {
  lang: 'es-GT',
  title: 'Si Hay Sistema',
  description: 'Documentación Factura Electrónica',
  base: '/',
  themeConfig: {
    logo: '/images/logo_vertical.png',
    home: '/',
    // navbar: [
    //     // nested group - max depth is 2
    //     {
    //         text: 'Group',
    //         children: [
    //             {
    //                 text: 'SubGroup',
    //                 children: ['/group/sub/foo.md', '/group/sub/bar.md'],
    //             },
    //         ],
    //     },
    //     // control when should the item be active
    //     {
    //         text: 'Group 2',
    //         children: [
    //             {
    //                 text: 'Always active',
    //                 link: '/',
    //                 // this item will always be active
    //                 activeMatch: '/',
    //             },
    //             {
    //                 text: 'Active on /foo/',
    //                 link: '/not-foo/',
    //                 // this item will be active when current route path starts with /foo/
    //                 // regular expression is supported
    //                 activeMatch: '^/foo/',
    //             },
    //         ],
    //     },
    // ],
    sidebar: [
      // SidebarItem
      {
        text: 'Disclaimer',
        link: '/introduccion/disclaimer.md',
      },
      {
        text: 'Introduccion',
        link: '/introduccion/instalar.md',
        children: [
          // SidebarItem
          {
            text: 'Instalación',
            link: '/introduccion/instalar.md',
            // children: [{
            //     text: 'Intro 2',
            //     link: '/introduccion/holaa.md'
            // }],
          },
          {
            text: 'Actualización',
            link: '/introduccion/actualizar.md',
          },
          {
            text: 'Desinstalación',
            link: '/introduccion/desinstalar.md',
          },
        ],
      },
      {
        text: 'Configuraciones',
        link: '/configuraciones/',
        children: [
          // SidebarItem
          {
            text: 'Compañía',
            link: '/configuraciones/compania.md',
          },
          {
            text: 'Series',
            link: '/configuraciones/series.md',
          },
          {
            text: 'Tablas de impuestos',
            link: '/configuraciones/impuestos.md',
          },
          {
            text: 'Productos',
            link: '/configuraciones/productos.md',
          },
          {
            text: 'Clientes y proveedores',
            link: '/configuraciones/clientes_proveedores.md',
          },
        ],
      },
      {
        text: 'Configurar App Factura Electrónica',
        link: '/configurar_app/',
        children: [
          {
            text: 'Credenciales y escenarios',
            link: '/configurar_app/configurar_credenciales.md',
          }
        ],
      },
      {
        text: 'Generación documentos electrónicos',
        link: '/generacion_docs_electronicos/',
        children: [
          {
            text: 'Factura Electrónica',
            link: '/generacion_docs_electronicos/factura_electronica.md',
          },
          {
            text: 'Nota Crédito Electrónica',
            link: '/generacion_docs_electronicos/nota_credito.md',
          },
          {
            text: 'Factura Cambiaria Electrónica',
            link: '/generacion_docs_electronicos/factura_cambiaria.md',
          },
          {
            text: 'Nota Débito Electrónica',
            link: '/generacion_docs_electronicos/nota_debito.md',
          },
          {
            text: 'Factura Especial Electrónica',
            link: '/generacion_docs_electronicos/factura_especial.md',
          },
          {
            text: 'Anulación Documentos Electrónicos',
            link: '/generacion_docs_electronicos/anulacion_documentos.md',
          },
        ],
      },
      {
        text: 'Como contribuir',
        link: '/contribuir/'
      }
    ],
  },
}