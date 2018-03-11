#include "simple.h"
#include "simple_lib.h"
#include "simple_so.h"


simple::simple_ui::simple_ui(BaseObjectType * cObj, 
    Glib::RefPtr<Gtk::Builder> const & builder)
    : Gtk::ApplicationWindow(cObj)
{
    Gtk::Button * button = nullptr;
    builder->get_widget("quit", button);
    if (button)
    {
        button->signal_clicked().connect(sigc::mem_fun(*this, & simple_ui::on_click));
    }

    simple::simple_lib lib;
    
    Gtk::Label * label = nullptr;
    builder->get_widget("static_a", label);
    if (label)
    {
        label->set_text(lib.get_a_string());
    }
    
    label = nullptr;
    builder->get_widget("static_b", label);
    if (label)
    {
        label->set_text(lib.get_b_string());
    }
    
    label = nullptr;
    builder->get_widget("dynamic_a", label);
    if (label)
    {
        label->set_text(get_a_string());
    }
    
    label = nullptr;
    builder->get_widget("dynamic_b", label);
    if (label)
    {
        label->set_text(get_b_string());
    }
}


void simple::simple_ui::on_click()
{
    // quit this bitch
    hide();
}

