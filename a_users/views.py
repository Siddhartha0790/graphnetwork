from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from allauth.account.utils import send_email_confirmation
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.contrib import messages
from .forms import *
from .models import Person,Profile
from neomodel import db
import json

def profile_view(request, username=None):
    if username:
        profile = get_object_or_404(User, username=username).profile
    else:
        try:
            profile = request.user.profile
        except:
            return redirect_to_login(request.get_full_path())
    return render(request, 'a_users/profile.html', {'profile':profile})


@login_required
def profile_edit_view(request):
    form = ProfileForm(instance=request.user.profile)  
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
        
    if request.path == reverse('profile-onboarding'):
        onboarding = True
    else:
        onboarding = False
      
    return render(request, 'a_users/profile_edit.html', { 'form':form, 'onboarding':onboarding })


@login_required
def profile_settings_view(request):
    return render(request, 'a_users/profile_settings.html')


@login_required
def profile_emailchange(request):
    
    if request.htmx:
        form = EmailForm(instance=request.user)
        return render(request, 'partials/email_form.html', {'form':form})
    
    if request.method == 'POST':
        form = EmailForm(request.POST, instance=request.user)

        if form.is_valid():
            
            # Check if the email already exists
            email = form.cleaned_data['email']
            if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                messages.warning(request, f'{email} is already in use.')
                return redirect('profile-settings')
            
            form.save() 
            
            # Then Signal updates emailaddress and set verified to False
            
            # Then send confirmation email 
            send_email_confirmation(request, request.user)
            
            return redirect('profile-settings')
        else:
            messages.warning(request, 'Form not valid')
            return redirect('profile-settings')
        
    return redirect('home')


@login_required
def profile_emailverify(request):
    send_email_confirmation(request, request.user)
    return redirect('profile-settings')


@login_required
def profile_delete_view(request):
    user = request.user
    if request.method == "POST":
        logout(request)
        user.delete()
        messages.success(request, 'Account deleted, what a pity')
        return redirect('home')
    
    return render(request, 'a_users/profile_delete.html')

@login_required
def rec_view(request):
    db.cypher_query("CALL gds.graph.project('myGraph', 'Person', 'FRIENDS_WITH');")
    

    # Run the PageRank Algorithm
    query = """
    CALL gds.pageRank.stream('myGraph')
    YIELD nodeId, score
    RETURN gds.util.asNode(nodeId).name AS Name, score
    ORDER BY score DESC;
    """
    
    results, _ = db.cypher_query(query)

    # Convert results to dictionary
    pagerank_dict = {record[0]: record[1] for record in results}
    print(pagerank_dict)
   
    db.cypher_query("CALL gds.graph.drop('myGraph');")
    
    
    my_user = Person.nodes.get(name = request.user.username)
    friends = my_user.friends.all()
    user = ''
    if request.method == "POST":
        form_type = request.POST.get('form_type')
        if form_type == 'form2':
            print(form_type)
           # print(request.POST)
            username = request.POST.get('search')
            user = User.objects.get(username=username)
            return render(request, 'a_users/recommendation.html' , {'user': user , 'friends':friends ,'dict1':pagerank_dict})
        
        else :
            print(form_type)
            person1 = request.user.username
            person2 = form_type
            guy1 = Person.nodes.get(name = person1)
            guy2 = Person.nodes.get(name = person2)
            
            guy1.friends.connect(guy2)
            return redirect('rec')
        
    return render(request, 'a_users/recommendation.html',{'user':user ,'friends':friends,'dict1':pagerank_dict})

def graph_view(request):
    query = """
    MATCH (n)
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN n, r, m
    """
    results, _ = db.cypher_query(query)
    
    nodes_dict = {}
    edges = []
    
    # Process each record
    for record in results:
        n, rel, m = record
       # print(rel)
        # Process first node (n)
        if n:
            node_id = n.id  # Neomodel node id
            if node_id not in nodes_dict:
                # Try to use the 'name' property, if available, otherwise a default string
                label = n.get('name', f"Node {node_id}")
                nodes_dict[node_id] = {
                    'id': node_id,
                    'label': label
                }
        # Process second node (m)
        if m:
            node2_id = m.id
            if node2_id not in nodes_dict:
                label = m.get('name', f"Node {node2_id}")
                nodes_dict[node2_id] = {
                    'id': node2_id,
                    'label': label
                }
        # If a relationship exists between n and m, add an edge.
        if rel is not None:
            print(rel)
        if rel is not None:
            try:
                rel_type = rel.type  # If available
            except AttributeError:
                rel_type = "RELATED"
            edges.append({
                'from': n.id,
                'to': m.id,
                'label': rel_type,
                'arrows': 'to',
                'color': { 'color': '#848484' }
            })
   
    context = {
        'nodes': json.dumps(list(nodes_dict.values())),
        'edges': json.dumps(edges)
    }
    return render(request, 'a_users/graph.html', context)


def remove(request,pk):
    print(pk)
    person1 = Person.nodes.get(name =pk)
    myuser = request.user
    person2 = Person.nodes.get(name = myuser.username)
    person2.friends.disconnect(person1)
    
    return redirect('rec')
    
def shortestpath(request,pk):
    query = """
    MATCH path = shortestPath((start:Person {name: $start})-[:FRIENDS_WITH*]-(end:Person {name: $end}))
    RETURN [node in nodes(path) | node.name] AS shortestPath;
    """
    me = request.user.username
    him = pk
    results, _ = db.cypher_query(query, {"start": me, "end": pk})
    print('function runs')
    print(results[0][0])
    print(type(results))
    path = results[0][0] # Example path

    nodes = [{"id": i, "label": city} for i, city in enumerate(path)]
    edges = [{"from": i, "to": i + 1} for i in range(len(path) - 1)]

    return render(request, 'a_users/shortestpath.html', {"nodes": nodes, "edges": edges})

    
 
