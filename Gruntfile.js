module.exports = function(grunt) {

    // 1. All configuration goes here 
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        // concat: {
        //     // 2. Configuration for concatinating files goes here.
        //     dist: {
        //         src: [
        //             'static/css/bootstrap.min.css', // Bootstrap
        //             'static/css/static.css'  // This specific file
        //         ],
        //         dest: 'static/css/production.css',
        //     }
        // },
        uncss: {
          dist: {
            src: ['templates/*', 'templates/admin/*', 'templates/partner/*', 'templates/feedback/*'],
            dest: 'static/css/tidy.css',
            options: {
              report: 'min' // optional: include to report savings
            }
          }
        }


        // uglify: {
        //     build: {
        //         src: 'static/css/production.css',
        //         dest: 'static/css/production.min.css',
        //     }
        // }

    });

    // 3. Where we tell Grunt we plan to use this plug-in.
    // grunt.loadNpmTasks('grunt-contrib-concat');
    grunt.loadNpmTasks('grunt-uncss');
    // grunt.loadNpmTasks('grunt-contrib-uglify');

    // 4. Where we tell Grunt what to do when we type "grunt" into the terminal.
    // grunt.registerTask('default', ['concat', 'uglify']);
    // grunt.registerTask('default', ['concat', 'uncss']);
    grunt.registerTask('default', ['uncss']);
};