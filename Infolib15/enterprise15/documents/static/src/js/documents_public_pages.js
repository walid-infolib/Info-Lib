odoo.define('documents.public_pages', function (require) {
"use strict";

// The purpose of this module is to adapt the image preview size on the public
// page of shared documents

require('web.dom_ready');

document.querySelectorAll('form[action*="/document/upload/"]').forEach(form => { 
    const input_csrf = document.createElement('input'); 
    input_csrf.type = 'hidden'; 
    input_csrf.name = 'csrf_token'; 
    input_csrf.value = odoo['csrf_token']; 
    form.prepend(input_csrf); 
});

var $container = $('#wrap .o_docs_single_container.o_has_preview');
if ($container.length === 0) {
    return;
}

var $parent = $container.parent();
var $image = $container.find('> img');
var $actions = $container.find('.o_docs_single_actions');

var checkResize = _.throttle(function () {
    $image.css('max-height', $parent.height() - $actions.outerHeight());
}, 100);

$image.on('load', function () {
    checkResize();
    $image.css('opacity', 1);
    $container.find('.o_loading_img').remove();
});

window.addEventListener('resize', checkResize, false);

});
