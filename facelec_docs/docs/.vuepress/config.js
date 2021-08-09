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
            text: 'Configuración de compañía',
            link: '/configuraciones/compania.md',
          },
          {
            text: 'Configuración de series',
            link: '/configuraciones/series.md',
          },
          {
            text: 'Configuración tablas de impuestos',
            link: '/configuraciones/impuestos.md',
          },
          {
            text: 'Configuración de productos',
            link: '/configuraciones/productos.md',
          },
          {
            text: 'Configuración de clientes y proveedores',
            link: '/configuraciones/clientes_proveedores.md',
          },
        ],
      }
    ],
  },
}