#include <iostream>
#include "simple.h"

int main(int argc, char **argv)
{
    auto app = Gtk::Application::create(argc, argv, "org.spacemeat.pyke");
    auto builder = Gtk::Builder::create();
    try
    {
        builder->add_from_file("res/simple.glade");
    }
    catch(const std::exception & ex)
    {
        std::cout << "Error loading glade file: " << ex.what() << std::endl;
        return 1;
    }
    
    simple::simple_ui * window = nullptr;
    try
    {
        builder->get_widget_derived("main", window);
        if (window)
        {
            app->run(*window, argc, argv);
        }
    }
    catch(const std::exception & ex)
    {
        delete window;
        window = nullptr;
    }
    
    delete window;
    return 0;
}

